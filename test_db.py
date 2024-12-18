from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

# Get database URI from environment
db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')

try:
    # Create engine and test connection
    engine = create_engine(db_uri)
    with engine.connect() as conn:
        print("Successfully connected to database!")
except Exception as e:
    print(f"Error connecting to database: {e}")