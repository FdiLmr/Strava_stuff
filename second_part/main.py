from flask import Flask, session, request, render_template, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from environs import Env
import requests
import os
import logging
import urllib.parse
from sqlalchemy import inspect, text
from sql_methods import init_db, db, test_conn_new, read_db, write_db_replace
from models import ProcessingStatus, Activity, AthleteStats  # Add this import
from visualisations import athletevsbest, athletevsbestimprovement
import random
from train_model import train_model

# Configure logging first
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def create_required_tables():
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        logger.info(f"Current tables: {existing_tables}")
        
        # Force create all tables from models
        db.create_all()
        
        # Initialize processing_status if empty
        if 'processing_status' in existing_tables:
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM processing_status")).scalar()
                logger.info(f"Processing status entries: {result}")
        
        # Initialize daily_limit if it doesn't exist
        if 'daily_limit' not in existing_tables:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS daily_limit (
                        daily INTEGER NOT NULL
                    )
                """))
                conn.execute(text("INSERT INTO daily_limit (daily) VALUES (0)"))
                conn.commit()
        
        # Log created tables
        updated_tables = inspect(db.engine).get_table_names()
        logger.info(f"Available tables after creation: {updated_tables}")

# Move create_tables call after all imports and configurations
create_required_tables()

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

@app.route('/update_tokens')
def update_tokens():
    from update_data import refresh_tokens
    res = refresh_tokens()
    print(res)
    return str(res), 200

def refresh_access_token(refresh_token):
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    r = requests.post("https://www.strava.com/oauth/token", data=params)
    if r.status_code == 200:
        return r.json()
    else:
        logger.error(f"Error refreshing access token: {r.text}")
        return None

@app.route("/authorization_successful")
def authorization_successful():
    from fetch_athlete_data import get_athlete, get_athlete_data_status, queue_athlete_for_processing
    
    logger.debug("Starting authorization_successful")
    logger.debug(f"Session contents: {session}")
    
    # Get the token from session with a default value of None
    token = session.get('token')
    refresh_token = session.get('refresh_token')
    logger.debug(f"Retrieved token from session: {token}")
    
    if token:
        logger.debug("Using existing token")
        athlete_data = get_athlete(token)
        if athlete_data is None:
            logger.debug("Token expired, refreshing token")
            response_data = refresh_access_token(refresh_token)
            if response_data:
                session['token'] = response_data['access_token']
                session['refresh_token'] = response_data['refresh_token']
                athlete_data = get_athlete(session['token'])
                if athlete_data is None:
                    return "Error requesting athlete data from Strava. Please try again later."
            else:
                logger.debug("Invalid refresh token, clearing session and redirecting to authorization page")
                session.clear()
                return redirect(authorize_url())
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
            session['refresh_token'] = response_data['refresh_token']
            logger.debug(f"Stored new token in session: {session['token']}")
            athlete_data = get_athlete(session['token'])
            if athlete_data is None:
                return "Error requesting athlete data from Strava. Please try again later."
        else:
            logger.error(f"Error fetching access token: {r.text}")
            return "Error fetching access token. Please try again later."
    
    try:
        athlete_id = athlete_data['id']
        logger.debug(f"Retrieved athlete_id: {athlete_id}")
        
        # Queue athlete for processing regardless of current status
        queue_result = queue_athlete_for_processing(
            athlete_id, 
            session['token'],
            session['refresh_token']
        )
        logger.info(f"Queue result: {queue_result}")
        
        # Check status after queueing
        athlete_data_status = get_athlete_data_status(athlete_id)
        logger.debug(f"Athlete data status: {athlete_data_status}")
        
        if athlete_data_status == 'processed':
            return render_template("render.html", athlete_id=athlete_id, random_num=str(os.urandom(8).hex()))
        else:
            return render_template('processing.html', status='processing')
            
    except KeyError as e:
        logger.error(f"Error accessing athlete data: {str(e)}")
        return "Error retrieving athlete data. Please try again later."

@app.route('/fetch_strava_data')
def fetch_strava_data():
    """Fetch raw data from Strava API and store in files/DB."""
    from update_data import fetch_strava_data
    res = fetch_strava_data()
    logger.info(f"Strava data fetch result: {res}")
    return str(res), 200

@app.route('/process_stored_data')
def process_stored_data():
    """Process data from stored files into analytics tables."""
    from update_data import process_stored_data
    res = process_stored_data()
    logger.info(f"Data processing result: {res}")
    return str(res), 200

@app.route('/reset_processing')
def reset_processing():
    try:
        processing_status = read_db('processing_status')
        processing_status['status'] = 'none'
        write_db_replace(processing_status, 'processing_status')
        return "Processing status reset successfully", 200
    except Exception as e:
        logger.error(f"Error resetting processing status: {e}")
        return f"Error: {str(e)}", 500

@app.route('/view_athletes')
def view_athletes():
    try:
        metadata_athletes = read_db('metadata_athletes')
        return render_template('view_athletes.html', athletes=metadata_athletes)
    except Exception as e:
        return f"Error retrieving athlete data: {str(e)}"

@app.route('/view_activities/<athlete_id>')
def view_activities(athlete_id):
    try:
        activities = db.session.query(Activity).filter_by(athlete_id=athlete_id).all()
        activities_data = [{
            'id': a.id,
            'name': a.name,
            'distance_raw': a.distance/1000,  # Raw numeric value for sorting
            'distance': f"{a.distance/1000:.2f}km",  # Formatted for display
            'time_raw': a.moving_time//60,  # Raw numeric value for sorting
            'time': f"{a.moving_time//60}min",  # Formatted for display
            'elapsed_time_raw': a.elapsed_time//60,  # Raw numeric value for sorting
            'elapsed_time': f"{a.elapsed_time//60}min",  # Formatted for display
            'date': a.start_date.strftime('%Y-%m-%d'),
            'type': a.type,
            'total_elevation_gain_raw': float(a.total_elevation_gain or 0),  # Raw numeric value
            'total_elevation_gain': f"{a.total_elevation_gain:.0f}m" if a.total_elevation_gain else "N/A",
            'average_speed_raw': float(a.average_speed * 3.6 if a.average_speed else 0),  # Raw numeric value
            'average_speed': f"{a.average_speed * 3.6:.1f}km/h" if a.average_speed else "N/A",
            'max_speed_raw': float(a.max_speed * 3.6 if a.max_speed else 0),  # Raw numeric value
            'max_speed': f"{a.max_speed * 3.6:.1f}km/h" if a.max_speed else "N/A",
            'avg_hr_raw': float(a.average_heartrate or 0),  # Raw numeric value
            'avg_hr': f"{a.average_heartrate:.0f}" if a.average_heartrate else "N/A",
            'max_hr_raw': float(a.max_heartrate or 0),  # Raw numeric value
            'max_hr': f"{a.max_heartrate:.0f}" if a.max_heartrate else "N/A"
        } for a in activities]
        
        return render_template(
            'activities.html',
            activities=activities_data,
            athlete_id=athlete_id
        )
    except Exception as e:
        return f"Error retrieving activities: {str(e)}"

@app.route('/view_stats/<athlete_id>')
def view_stats(athlete_id):
    try:
        stats = db.session.get(AthleteStats, athlete_id)
        if stats:
            return render_template('stats.html', stats=stats)
        return "No stats found for this athlete"
    except Exception as e:
        return f"Error retrieving stats: {str(e)}"

@app.route('/reset_activities')
def reset_activities():
    try:
        with app.app_context():
            # Clear activities and stats tables
            db.session.query(Activity).delete()
            db.session.query(AthleteStats).delete()
            
            # Reset processing status to 'none'
            processing_status = read_db('processing_status')
            processing_status['status'] = 'none'
            write_db_replace(processing_status, 'processing_status')
            
            # Reset API call counter
            daily_limit = read_db('daily_limit')
            daily_limit.at[0, 'daily'] = 0
            write_db_replace(daily_limit, 'daily_limit')
            
            db.session.commit()
            
            logger.info("Successfully reset activities and processing status")
            return "Activities cleared and reset successfully. You can now run the processing again.", 200
    except Exception as e:
        logger.error(f"Error resetting activities: {e}")
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/reset_database')
def reset_database():
    from sql_methods import reset_database
    
    logger.info("Starting database reset")
    if reset_database():
        logger.info("Database reset successful")
        return "Database reset successful. Tables have been cleared.", 200
    else:
        return "Error resetting database", 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.context_processor
def inject_user():
    """Make session available to all templates"""
    return dict(session=session)

@app.route('/visualize/performance/<athlete_id>')
def visualize_performance(athlete_id):
    """Generate and return performance visualization."""
    try:
        bytes_image = athletevsbest(athlete_id)
        if bytes_image is None:
            return "Error generating visualization", 500
        return send_file(bytes_image, mimetype='image/png')
    except Exception as e:
        logger.error(f"Error in performance visualization: {e}")
        return f"Error: {str(e)}", 500

@app.route('/visualize/improvement/<athlete_id>')
def visualize_improvement(athlete_id):
    """Generate and return improvement visualization."""
    try:
        bytes_image = athletevsbestimprovement(athlete_id)
        if bytes_image is None:
            return "Error generating visualization", 500
        return send_file(bytes_image, mimetype='image/png')
    except Exception as e:
        logger.error(f"Error in improvement visualization: {e}")
        return f"Error: {str(e)}", 500

@app.route('/visualize/<athlete_id>')
def visualize(athlete_id):
    """Render the visualization page for an athlete."""
    return render_template(
        'render.html',
        athlete_id=athlete_id,
        random_num=random.randint(1, 1000000)  # Cache busting
    )

@app.route('/model_results/<athlete_id>')
def model_results(athlete_id):
    """Display model results and SHAP plots for an athlete."""
    try:
        # Check if model outputs exist
        model_outputs = read_db('model_outputs')
        if model_outputs.empty or not any(model_outputs['athlete_id'] == athlete_id):
            # Train model if no results exist
            results = train_model(athlete_id)
            return render_template('model_results.html', 
                                athlete_id=athlete_id,
                                model_outputs=results)
        else:
            # Get existing results
            athlete_outputs = model_outputs[model_outputs['athlete_id'] == athlete_id]
            results = {
                'absolute_vdot_score': athlete_outputs[athlete_outputs['y_name'] == 'absolute_vdot']['model_score'].iloc[0],
                'vdot_change_score': athlete_outputs[athlete_outputs['y_name'] == 'vdot_change']['model_score'].iloc[0]
            }
            return render_template('model_results.html',
                                athlete_id=athlete_id,
                                model_outputs=results)
    except Exception as e:
        logger.error(f"Error displaying model results: {e}")
        return render_template('model_results.html',
                            athlete_id=athlete_id,
                            error_message=str(e))

@app.route('/train_model/<athlete_id>')
def train_model_route(athlete_id):
    """Train model for a specific athlete."""
    try:
        results = train_model(athlete_id)
        return render_template('model_results.html',
                            athlete_id=athlete_id,
                            model_outputs=results)
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return render_template('model_results.html',
                            athlete_id=athlete_id,
                            error_message=str(e))

if __name__ == '__main__':
    app.run(debug=True)