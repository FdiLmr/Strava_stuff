""" 
Basics:
    
To get data on athletes, you will have to make an application and request that
athletes sign in with Strava, and grant your application certain permission
using OAuth 2.0. You can get data on yourself without authentication for testing purposes.

Strava API usage is limited on a per-application basis using both a 
15-minute and daily request limit. 
The default rate limit allows 
- 200 requests every 15 minutes
- with up to 2000 requests per day. 
- aka 13 req/min for 2h30min 
- to a maximum of 6 hours per access token
- this script uses x requests for me, an athlete with many activities. 
so one ingestion per day is possible, worst case
An application’s 15-minute limit is reset at natural 15-minute intervals corresponding to 0, 15, 30 and 45 minutes after the hour. The daily limit resets at midnight UTC.


"""
import os
import requests
from sql_methods import read_db, write_db_replace


CLIENT_ID = os.environ.get('CLIENT_ID')
client_id = CLIENT_ID #unique identifier for app


def get_athlete(bearer_token):
    
    url = 'https://www.strava.com/api/v3/athlete'
    data = ''
    headers = {"Authorization": "Bearer " + bearer_token}
    response = requests.get(url, data=data, headers=headers)
    athlete_data = response.json()
    
    try:
        athlete_id = athlete_data['id']
        print(str(athlete_id))
    except Exception:
        print ("Error requesting athlete data from Strava")
        return 1
    
    return athlete_data

def get_athlete_data_status(athlete_id):
    
    processing_status = read_db('processing_status')
    
    if str(athlete_id) in processing_status["athlete_id"].values:        
        ingest_status = processing_status[processing_status["athlete_id"] == str(athlete_id)]["status"].values[0]
        return ingest_status
    
    return "to process"

def queue_athlete_for_processing(athlete_id, bearer_token, refresh_token):

    import pandas as pd  
    
    processing_status = read_db('processing_status')
    new_row = pd.DataFrame([{
        'athlete_id': athlete_id,
        'status': 'none',
        'bearer_token': bearer_token,
        'refresh_token': refresh_token
    }])
    processing_status = pd.concat([processing_status, new_row], ignore_index=True)
    write_db_replace(processing_status, 'processing_status')           
    
    return "none"