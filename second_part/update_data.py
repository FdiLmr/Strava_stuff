from sql_methods import write_db_replace, write_db_insert, read_db, db
from athlete_data_transformer import transform_athlete_data
import requests
import pandas as pd
import time
import os
import logging
from models import Activity, AthleteStats
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)


def refresh_tokens():    
    try:
        processing_status = read_db('processing_status')
        
        for index, row in processing_status.iterrows():
            if row['athlete_id'] != 0 and row['status'] == "none":
                params = {
                    "client_id": os.environ.get('CLIENT_ID'),
                    "client_secret": os.environ.get('CLIENT_SECRET'),
                    "refresh_token": row['refresh_token'],
                    "grant_type": "refresh_token"
                }
                
                r = requests.post("https://www.strava.com/oauth/token", data=params)
                r.raise_for_status()
                response_data = r.json()
                
                processing_status.at[index,'bearer_token'] = response_data['access_token']
                processing_status.at[index,'refresh_token'] = response_data['refresh_token']
        
        write_db_replace(processing_status, 'processing_status')
        return 0
    except Exception as e:
        logger.error(f"Error refreshing tokens: {e}")
        return 1

def get_unprocessed_activities(activity_list, existing_ids, limit=90):
    """Helper function to get activities we haven't processed yet"""
    new_activities = []
    for activity in activity_list:
        if len(new_activities) >= limit:
            break
        if activity['id'] not in existing_ids:
            new_activities.append(activity)
    return new_activities

def update_data():          
    start_time = time.time()
    total_activities_processed = 0
    athletes_processed = 0
    
    # Get initial API call count
    daily_limit = read_db('daily_limit')    
    initial_api_calls = int(daily_limit.iloc[0,0])
    logger.info(f"Starting data processing. Initial API calls today: {initial_api_calls}/25000")
    
    if (initial_api_calls > 25000):
        logger.error("API LIMIT EXCEEDED")
        return "api limit exceeded"
    
    processing_status = read_db('processing_status')
    athletes_to_process = len(processing_status[processing_status['status'] == 'none'])
    logger.info(f"Found {athletes_to_process} athletes to process")
    
    current_api_calls = initial_api_calls
    
    for index, row in processing_status.iterrows():
        with current_app.app_context():  # Add application context
            athlete_id = int(row['athlete_id'])
            
            if athlete_id != 0 and row['status'] == "none":
                athlete_start_time = time.time()
                logger.info(f"Processing athlete {athlete_id}")
                
                bearer_token = row['bearer_token']            
                print ('processing athlete ' + str(athlete_id))
                headers = {"Authorization": "Bearer " + bearer_token}
            
                processing_status.at[index, 'status'] = 'processing'
                
                try:
                    
                    """
                    GET ATHLETE DATA
                    ----------
                    """
                    url = 'https://www.strava.com/api/v3/athlete'
                    data = ''
                    headers = {"Authorization": "Bearer " + bearer_token}
                    response = requests.get(url, data=data, headers=headers)
                    athlete_data = response.json()           
                    
                    """
                    GET ATHLETE ZONES
                    -----------
                    """
                    url = 'https://www.strava.com/api/v3/athlete/zones'
                    data = ''
                    response = requests.get(url, data=data, headers=headers)
                    athlete_zones = response.json()                    
                    current_api_calls += 1
                    
                    
                    """
                    GET ATHLETE STATS
                    -----------
                    """
                    url = 'https://www.strava.com/api/v3/athletes/' + str(athlete_id) + '/stats'
                    response = requests.get(url, headers=headers)
                    athlete_stats = response.json()
                    
                    # Store stats in database
                    try:
                        stats = AthleteStats(
                            athlete_id=str(athlete_id),
                            recent_run_totals=athlete_stats.get('recent_run_totals'),
                            all_run_totals=athlete_stats.get('all_run_totals'),
                            all_ride_totals=athlete_stats.get('all_ride_totals')
                        )
                        db.session.merge(stats)
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Error storing stats: {e}")
                        db.session.rollback()
                    
                    """
                    GET ACTIVITY LIST
                    -----------------
                    """
                    activities_to_process = 90  # Safe limit for 15-min window
                    all_activities = []
                    page = 1
                    
                    # First, get all activities IDs we already have
                    existing_activities = db.session.query(Activity.id).filter_by(athlete_id=str(athlete_id)).all()
                    existing_ids = {a[0] for a in existing_activities}
                    logger.info(f"Found {len(existing_ids)} existing activities")
                    
                    # Keep fetching pages until we have enough new activities
                    while True:
                        url = f'https://www.strava.com/api/v3/athlete/activities?per_page=100&page={page}'
                        response = requests.get(url, headers=headers)
                        this_response = response.json()
                        current_api_calls += 1
                        
                        if not this_response:  # No more activities
                            break
                            
                        all_activities.extend(this_response)
                        
                        # Check if we have enough new activities
                        unprocessed = get_unprocessed_activities(all_activities, existing_ids, activities_to_process)
                        if len(unprocessed) >= activities_to_process:
                            break
                            
                        page += 1
                        
                        # Rate limiting between pages
                        time.sleep(1.5)  # Ensure we don't hit rate limits
                    
                    logger.info(f"Found {len(all_activities)} total activities, {len(unprocessed)} new ones")
                    
                    # Store what we found, even if zero new activities
                    activities = []
                    new_activities_count = 0
                    
                    if len(unprocessed) > 0:
                        """
                        GET DETAILED ACTIVITY DATA
                        ------------------------
                        """
                        for activity in unprocessed[:activities_to_process]:
                            start = time.time()
                            
                            activity_id = activity['id']
                            url = f'https://www.strava.com/api/v3/activities/{activity_id}'
                            response = requests.get(url, headers=headers)
                            this_response = response.json()
                            activities.append(this_response)
                            current_api_calls += 1
                            new_activities_count += 1
                            
                            # Store activity in database
                            try:
                                activity = Activity(
                                    id=this_response['id'],
                                    athlete_id=str(athlete_id),
                                    name=this_response.get('name'),
                                    distance=this_response.get('distance'),
                                    moving_time=this_response.get('moving_time'),
                                    elapsed_time=this_response.get('elapsed_time'),
                                    total_elevation_gain=this_response.get('total_elevation_gain'),
                                    type=this_response.get('type'),
                                    start_date=datetime.strptime(this_response.get('start_date'), '%Y-%m-%dT%H:%M:%SZ'),
                                    average_speed=this_response.get('average_speed'),
                                    max_speed=this_response.get('max_speed'),
                                    average_heartrate=this_response.get('average_heartrate'),
                                    max_heartrate=this_response.get('max_heartrate'),
                                    activity_data=this_response
                                )
                                db.session.merge(activity)
                            except Exception as e:
                                logger.error(f"Error storing activity {activity_id}: {e}")
                                continue
                                
                            # Rate limiting
                            end = time.time()
                            remain = start + 1.5 - end
                            if remain > 0:
                                time.sleep(remain)
                        
                        try:
                            db.session.commit()
                            logger.info(f"Successfully stored {new_activities_count} new activities")
                        except Exception as e:
                            logger.error(f"Error committing activities to database: {e}")
                            db.session.rollback()
                            raise
                    else:
                        logger.info(f"No new activities to process for athlete {athlete_id}")
                    
                    # Always continue with metadata and stats
                    athlete_data["_Zones"] = athlete_zones
                    athlete_data["_Stats"] = athlete_stats
                    athlete_data["_Activities"] = activities
                    
                except Exception as ex:                    
                    daily_limit.at[0, 'daily'] = current_api_calls
                    write_db_replace(daily_limit,'daily_limit')                                
                    processing_status.at[index, 'status'] = 'none'
                    return ('failure processing athlete ' + str(row['athlete_id']) + ': ' + str(ex))          
                                                
                transform_athlete_data(athlete_id, athlete_data)
                
                # Update status to processed
                processing_status.at[index, 'status'] = 'processed'
                write_db_replace(processing_status, 'processing_status')
                
                daily_limit.at[0, 'daily'] = current_api_calls
                write_db_replace(daily_limit, 'daily_limit')       

                print ('successfully processed athlete ' + str(athlete_id))     

                # After successfully processing activities
                activities_count = len(activities)
                total_activities_processed += activities_count
                athletes_processed += 1
                processing_time = time.time() - athlete_start_time
                
                logger.info(f"""
                    Athlete {athlete_id} processing complete:
                    - Activities processed: {activities_count}
                    - Processing time: {processing_time:.2f} seconds
                    - Average time per activity: {processing_time/activities_count:.2f} seconds
                    - Current API calls: {current_api_calls}/25000
                """)
    
    total_time = time.time() - start_time
    api_calls_made = current_api_calls - initial_api_calls
    
    # Fix division by zero
    avg_time_per_athlete = total_time / athletes_processed if athletes_processed > 0 else 0
    avg_time_per_activity = total_time / total_activities_processed if total_activities_processed > 0 else 0
    
    summary = f"""
    Processing Complete:
    ===================
    Athletes processed: {athletes_processed}/{athletes_to_process if athletes_to_process > 0 else 'None'}
    Total activities: {total_activities_processed}
    Total processing time: {total_time:.2f} seconds
    Average time per athlete: {avg_time_per_athlete:.2f} seconds
    Average time per activity: {avg_time_per_activity:.2f} seconds
    API calls made: {api_calls_made}
    Initial API calls: {initial_api_calls}
    Final API calls: {current_api_calls}
    Remaining API calls: {25000 - current_api_calls}
    """
    
    logger.info(summary)
    return summary