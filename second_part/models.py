from sql_methods import db

class ProcessingStatus(db.Model):
    __tablename__ = 'processing_status'
    
    athlete_id = db.Column(db.String(100), primary_key=True)
    status = db.Column(db.String(50))
    bearer_token = db.Column(db.String(255))
    refresh_token = db.Column(db.String(255))

    def __repr__(self):
        return f'<ProcessingStatus {self.athlete_id}>' 