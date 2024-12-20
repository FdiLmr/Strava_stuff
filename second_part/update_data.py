from sql_methods import write_db_replace, write_db_insert, read_db
import requests
import pandas as pd
import time
import os
#from feature_engineer_athlete import feature_engineer

def refresh_tokens():
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
            processing_status.at[index, 'bearer_token'] = r.json()['access_token']
            processing_status.at[index, 'refresh_token'] = r.json()['refresh_token']

    write_db_replace(processing_status, 'processing_status')
    return 0

def update_data():
    # refresh_tokens()
    daily_limit = read_db('daily_limit')
    current_api_calls = int(daily_limit.iloc[0, 0])

    if current_api_calls > 25000:
        print("API LIMIT EXCEEDED")
        return "api limit exceeded"

    processing_status = read_db('processing_status')

    for index, row in processing_status.iterrows():
        athlete_id = int(row['athlete_id'])

        if athlete_id != 0 and row['status'] == "none":
            bearer_token = row['bearer_token']
            print('processing athlete ' + str(athlete_id))
            headers = {"Authorization": "Bearer " + bearer_token}
            processing_status.at[index, 'status'] = 'processing'

            try:
                # GET ATHLETE DATA
                url = 'https://www.strava.com/api/v3/athlete'
                response = requests.get(url, headers=headers)
                athlete_data = response.json()

                # GET ATHLETE ZONES
                url = 'https://www.strava.com/api/v3/athlete/zones'
                response = requests.get(url, headers=headers)
                athlete_zones = response.json()
                current_api_calls += 1

                # GET ATHLETE STATS
                url = f'https://www.strava.com/api/v3/athletes/{athlete_id}/stats'
                response = requests.get(url, headers=headers)
                athlete_stats = response.json()
                current_api_calls += 1

                # GET ACTIVITY LIST
                url = 'https://www.strava.com/api/v3/athlete/activities?per_page=40&page=1'
                response = requests.get(url, headers=headers)
                activity_pg = response.json()
                current_api_calls += 1

                pg = 1
                while len(activity_pg) > 3:
                    start = time.time()
                    pg += 1
                    url = f'https://www.strava.com/api/v3/athlete/activities?per_page=40&page={pg}'
                    response = requests.get(url, headers=headers)
                    this_response = response.json()
                    activity_pg += this_response
                    current_api_calls += 1

                    # rate limiting part 2
                    end = time.time()
                    remain = start + 1.5 - end
                    if remain > 0:
                        time.sleep(remain)

                print(activity_pg)
                if len(activity_pg) > 20:
                    # GET ALL ACTIVITIES FOR ATHLETE
                    activities = []
                    for x in activity_pg:
                        # rate limiting part 1
                        start = time.time()
                        activity_id = x['id']
                        url = f'https://www.strava.com/api/v3/activities/{activity_id}'
                        response = requests.get(url, headers=headers)
                        activities.append(response.json())
                        current_api_calls += 1

                        # rate limiting part 2
                        end = time.time()
                        remain = start + 1.5 - end
                        if remain > 0:
                            time.sleep(remain)

                    # CREATE ATHLETE FILE AND WRITE
                    athlete_data["_Zones"] = athlete_zones
                    athlete_data["_Stats"] = athlete_stats
                    athlete_data["_Activities"] = activities
                else:
                    return "athlete rejected - too few activities"

            except Exception as ex:
                daily_limit.at[0, 'daily'] = current_api_calls
                write_db_replace(daily_limit, 'daily_limit')
                processing_status.at[index, 'status'] = 'none'
                return f'failure processing athlete {row["athlete_id"]}: {str(ex)}'

            feature_engineer(athlete_id, athlete_data)
            daily_limit.at[0, 'daily'] = current_api_calls
            write_db_replace(daily_limit, 'daily_limit')
            print('successfully processed athlete ' + str(athlete_id))

    return "done / nobody to ingest"