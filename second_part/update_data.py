from sql_methods import write_db_replace, write_db_insert, read_db
from athlete_data_transformer import transform_athlete_data
import requests
import pandas as pd
import time
import os
import logging

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
                Not sure if any of this is relevant
                """
                url = 'https://www.strava.com/api/v3/athletes/' + str(athlete_id) + '/stats'
                data = ''
                response = requests.get(url, data=data, headers=headers)
                athlete_stats = response.json()    
                current_api_calls += 1                    
                
                """
                GET ACTIVITY LIST
                -----------------
                """
                url = 'https://www.strava.com/api/v3/athlete/activities?per_page=25&page=1'
                data = ''
                response = requests.get(url, data=data, headers=headers)
                this_response = response.json()
                activity_pg = this_response[:25]  # Limit to 25 activities
                current_api_calls += 1
                
                # Remove the pagination loop since we're only taking 25 activities
                
                print(activity_pg)
                if (len(activity_pg) > 0):  # Changed from 20 to 0 since we're limiting to 25
                    
                    """
                    GET ALL ACTIVITIES FOR ATHLETE
                    ------------------------------
                    """
                    
                    activities = []
                    
                    for x in activity_pg:
                        #rate limiting part 1 
                        
                        start = time.time()
                        
                        activity_id = x['id']
                        url = 'https://www.strava.com/api/v3/activities/' + str(activity_id)
                        data = ''
                        response = requests.get(url, data=data, headers=headers)
                        this_response = response.json()
                        activities.append(this_response)
                        current_api_calls += 1  
                        
                        #rate limiting part 2
                        end = time.time()
                        remain = start + 1.5 - end
                        if remain > 0:
                            time.sleep(remain)
                        
                        """
                        CREATE ATHLETE FILE AND WRITE
                        -----------------------------
                        """
                        
                    athlete_data["_Zones"] = athlete_zones
                    athlete_data["_Stats"] = athlete_stats
                    athlete_data["_Activities"] = activities
                       
                else:
                    return "athlete rejected - too few activities"
                
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