from flask import Flask, session, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from environs import Env
import requests
import os
import logging
import urllib.parse
from sql_methods import init_db, db, test_conn_new

# Load environment variables from .env file
env = Env()
env.read_env()

# Get environment variables
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')

app = Flask(__name__)

# Configure session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
Session(app)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{os.environ.get("DB_USER")}:{os.environ.get("DB_PASS")}@{os.environ.get("DB_HOST")}/{os.environ.get("DB_NAME")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
init_db(app)

# Create tables
with app.app_context():
    db.create_all()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def render_index():
    return render_template('index.html')

@app.route('/about')
def render_about():
    return render_template('about.html')

@app.route('/sql')
def render_sql_test():
    return test_conn_new()

def authorize_url():
    """Generate authorization uri"""
    app_url = os.getenv('APP_URL', 'http://localhost:5000')
    logger.debug(f"APP_URL={app_url}")
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": f"{app_url}/authorization_successful",
        "scope": "read,profile:read_all,activity:read",
        "state": 'https://github.com/sladkovm/strava-oauth',
        "approval_prompt": "force"
    }
    values_url = urllib.parse.urlencode(params)
    base_url = 'https://www.strava.com/oauth/authorize'
    rv = base_url + '?' + values_url
    logger.debug(f"Authorization URL: {rv}")
    return rv

@app.route("/login")
def login():
    """Redirect user to the Strava Authorization page"""
    logger.debug(f"Using CLIENT_ID: {CLIENT_ID}")
    return redirect(authorize_url())

@app.route("/authorization_successful")
def authorization_successful():
    from fetch_athlete_data import get_athlete, get_athlete_data_status, queue_athlete_for_processing
    
    logger.debug("Starting authorization_successful")
    logger.debug(f"Session contents: {session}")
    
    # Get the token from session with a default value of None
    token = session.get('token')
    logger.debug(f"Retrieved token from session: {token}")
    
    if token:
        logger.debug("Using existing token")
        athlete_data = get_athlete(token)
    else:
        logger.debug("No existing token, exchanging code for token")
        code = request.args.get('code')
        if not code:
            logger.error("No authorization code received")
            return "Authorization failed. No code received."

        params = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        logger.debug(f"Token exchange parameters: {params}")
        r = requests.post("https://www.strava.com/oauth/token", data=params)
        logger.debug(f"Token exchange response: {r.text}")
        
        if r.status_code == 200:
            response_data = r.json()
            session['token'] = response_data['access_token']
            logger.debug(f"Stored new token in session: {session['token']}")
            athlete_data = get_athlete(session['token'])
            queue_athlete_for_processing(athlete_data['id'], response_data['access_token'], response_data['refresh_token'])
        else:
            logger.error(f"Error fetching access token: {r.text}")
            return "Error fetching access token. Please try again later."
    
    try:
        athlete_id = athlete_data['id']
        logger.debug(f"Retrieved athlete_id: {athlete_id}")
    except KeyError as e:
        logger.error(f"Error accessing athlete data: {str(e)}")
        return "Error retrieving athlete data. Please try again later."
    
    athlete_data_status = get_athlete_data_status(athlete_id)
    logger.debug(f"Athlete data status: {athlete_data_status}")
    
    if athlete_data_status == 'processed':
        return render_template("render.html", athlete_id=athlete_id, random_num=str(os.urandom(8).hex()))
    elif athlete_data_status in ['processing', 'none']:
        return render_template('processing.html', status='processing')
    else:
        return render_template('processing.html', status='none')

if __name__ == '__main__':
    app.run(debug=True)