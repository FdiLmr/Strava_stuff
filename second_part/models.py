from sql_methods import db

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

class FeaturesBlock(db.Model):
    __tablename__ = 'features_blocks'
    
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.String(100))
    block_id = db.Column(db.String(100))
    y_vdot_delta = db.Column(db.Float)
    y_vdot = db.Column(db.Float)
    f_slope_run_distance = db.Column(db.Float)
    f_slope_run_time = db.Column(db.Float)
    f_slope_mean_run_hr = db.Column(db.Float)
    f_taper_factor_run_distance = db.Column(db.Float)
    f_taper_factor_run_time = db.Column(db.Float)
    f_taper_factor_mean_run_hr = db.Column(db.Float)

    def __repr__(self):
        return f'<FeaturesBlock {self.block_id}>'

class MetadataBlock(db.Model):
    __tablename__ = 'metadata_blocks'
    
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.String(100))
    vdot = db.Column(db.Float)
    vdot_delta = db.Column(db.Float)
    predicted_marathon_time = db.Column(db.Float)
    pb_date = db.Column(db.DateTime)
    block_id = db.Column(db.String(100))

    def __repr__(self):
        return f'<MetadataBlock {self.block_id}>'

class ModelOutput(db.Model):
    __tablename__ = 'model_outputs'
    
    id = db.Column(db.Integer, primary_key=True)
    y_name = db.Column(db.String(100))
    feature_name = db.Column(db.String(100))
    importance = db.Column(db.Float)

    def __repr__(self):
        return f'<ModelOutput {self.y_name}_{self.feature_name}>'