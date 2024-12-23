from flask import current_app
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from sqlalchemy import text, create_engine, inspect
import os
import logging

logger = logging.getLogger(__name__)
db = SQLAlchemy()

def init_db(app):
    db.init_app(app)

def get_db_connection():
    return create_engine(f'mysql+pymysql://{os.environ.get("DB_USER")}:{os.environ.get("DB_PASS")}@{os.environ.get("DB_HOST")}/{os.environ.get("DB_NAME")}')

def read_db(table_name):
    try:
        engine = get_db_connection()
        logger.info(f"Reading from table {table_name}")
        
        # Check if table exists first
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            logger.info(f"Table {table_name} does not exist yet, returning empty DataFrame")
            return pd.DataFrame()
        
        df = pd.read_sql_table(table_name, engine)
        logger.info(f"Read {len(df)} rows from {table_name}")
        return df
    except Exception as e:
        logger.error(f"Error reading from database: {e}", exc_info=True)
        # Return empty DataFrame instead of raising error
        return pd.DataFrame()

def write_db_replace(df, table_name):
    try:
        engine = get_db_connection()
        logger.info(f"Writing {len(df)} rows to table {table_name}")
        logger.debug(f"DataFrame contents: {df.to_dict()}")
        
        # Convert DataFrame to SQL
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists='replace',
            index=False
        )
        
        # Verify write
        with engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            logger.info(f"Written {count} rows to {table_name}")
        
        return True
    except Exception as e:
        logger.error(f"Error writing to database: {e}", exc_info=True)
        raise

def write_db_insert(df, table_name):
    try:
        engine = get_db_connection()
        df.to_sql(name=table_name, con=engine, if_exists='append', index=False)
        return True
    except Exception as e:
        logger.error(f"Error inserting into database: {e}")
        raise

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
        engine = get_db_connection()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "Connection successful!"
    except Exception as e:
        return f"Connection failed: {str(e)}"

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