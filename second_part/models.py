from second_part.sql_methods import db

class ProcessingStatus(db.Model):
    __tablename__ = 'processing_status'
    
    athlete_id = db.Column(db.String(100), primary_key=True)
    status = db.Column(db.String(50))
    bearer_token = db.Column(db.String(255))
    refresh_token = db.Column(db.String(255))

    def __repr__(self):
        return f'<ProcessingStatus {self.athlete_id}>'

class AthleteStats(db.Model):
    __tablename__ = 'athlete_stats'
    
    athlete_id = db.Column(db.String(100), primary_key=True)
    recent_run_totals = db.Column(db.JSON)
    all_run_totals = db.Column(db.JSON)
    all_ride_totals = db.Column(db.JSON)
    
    def __repr__(self):
        return f'<AthleteStats {self.athlete_id}>'

class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.BigInteger, primary_key=True)
    athlete_id = db.Column(db.String(100))
    name = db.Column(db.String(255))
    distance = db.Column(db.Float)
    moving_time = db.Column(db.Integer)
    elapsed_time = db.Column(db.Integer)
    total_elevation_gain = db.Column(db.Float)
    type = db.Column(db.String(50))
    start_date = db.Column(db.DateTime)
    average_speed = db.Column(db.Float)
    max_speed = db.Column(db.Float)
    average_heartrate = db.Column(db.Float)
    max_heartrate = db.Column(db.Float)
    activity_data = db.Column(db.JSON)  # Store full activity JSON
    
    def __repr__(self):
        return f'<Activity {self.id}>'