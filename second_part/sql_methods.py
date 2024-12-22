from flask import current_app
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from sqlalchemy import text

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)

def read_db(df_name):    
    query = f'SELECT * FROM {df_name}'
    with current_app.app_context():
        x = pd.read_sql_query(query, db.engine)
    return x

def write_db_replace(df, name):
    with current_app.app_context():
        df.to_sql(name, con=db.engine, if_exists='replace', index=False)
    
def write_db_insert(df, name):
    with current_app.app_context():
        df.to_sql(name, con=db.engine, if_exists='append', index=False)

def delete_rows(df_name):    
    try:
        with current_app.app_context():
            with db.engine.connect() as connection:
                result = connection.execute(text(f'DELETE FROM {df_name};'))
                return True
    except Exception as e:
        logger.error(f"Error deleting rows from {df_name}: {e}")
        return False

def test_conn_new():    
    try:
        with current_app.app_context():
            with db.engine.connect() as connection:
                result = connection.execute(text('SHOW TABLES'))
                tables = result.fetchall()
                return 'pass' if tables else 'no tables found'
    except Exception as e:
        return str(e)

"""
processing_status = read_db('processing_status')
processing_status_index = processing_status[processing_status['athlete_id']==str(int(athlete_id))].index.values.astype(int)[0]    
processing_status.at[processing_status_index, 'status'] = 'processed'
write_db_replace(processing_status, 'processing_status')


SHOW / DROP TABLES

rs = engine.execute('show tables')

for row in rs:
    print (row)

rs = engine.execute('drop table metadata_athletes')
rs = engine.execute('drop table metadata_blocks')
rs = engine.execute('drop table all_athlete_activities')
rs = engine.execute('drop table all_athlete_weeks')
rs = engine.execute('drop table features_activities')
rs = engine.execute('drop table features_weeks')
rs = engine.execute('drop table features_blocks')
rs = engine.execute('drop table average_paces_and_hrs')


"""