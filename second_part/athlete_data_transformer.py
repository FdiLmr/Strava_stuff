"""
Initiating the three main dataframes:
    athlete_metadata - stores constants for the athlete, e.g. HR zones
    athlete_training_blocks - stores info about a training block between races
    athlete_training_week - stores info about a training week within a training block
"""

import pandas as pd 
import ast
import numpy as np
import logging
from sql_methods import write_db_replace, read_db

logger = logging.getLogger(__name__)

def transform_athlete_data(athlete_id, athlete_data, populate_all_from_files=0):
    
    """
    Dataframe description:
        metadata_athletes: just athlete name, zones, etc. not for model training
        metadata_blocks: same, at block level
        
        features_activities: features per activity. trying not to lose any data at this level, so it's not turned into HR zones, etc
        features_weeks: a week of training, losing/averaging some data
        features_blocks: a block of data, the main dataset that predicts an increase in vdot. a lot of data averaging, cleaning etc 
    """
    
    if(populate_all_from_files == 1):
        file = './data/' + str(athlete_id) + '.txt'  
        
        f=open(file, 'r', encoding="utf8")  
        file_data = f.read()   
        athlete_data = ast.literal_eval(file_data)
        f.close()
    
    metadata_athletes = pd.DataFrame()
    metadata_blocks = pd.DataFrame()
    all_athlete_activities = pd.DataFrame()
    all_athlete_weeks = pd.DataFrame()
    features_activities = pd.DataFrame()
    features_weeks = pd.DataFrame()
    features_blocks = pd.DataFrame()
    regressors = dict()
    average_paces_and_hrs = pd.DataFrame()
    
    
    dict_data = athlete_data
    
    """
    SAVE ATHLETE METADATA
    """    
    new_athlete_data = pd.DataFrame([
        [dict_data['id'], dict_data['sex'], dict_data['weight'], dict_data['_Zones']['heart_rate']['zones']]
    ], columns=['id','sex', 'weight', 'zones'])
    
    try:
        existing_metadata = read_db('metadata_athletes')
        metadata_athletes = pd.concat([existing_metadata, new_athlete_data], ignore_index=True)
    except Exception as e:
        logger.warning(f"Could not read existing metadata: {e}")
        metadata_athletes = new_athlete_data

    # Convert all columns to strings using map instead of applymap
    metadata_athletes = metadata_athletes.astype(str)
    write_db_replace(metadata_athletes, 'metadata_athletes')
