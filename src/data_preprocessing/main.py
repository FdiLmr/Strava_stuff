import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional
from .utils import calculate_pace, pace_to_speed

class StravaDataPreprocessor:
    def __init__(self, csv_path: str):
        """Initialize the preprocessor with path to Strava CSV data."""
        self.raw_data = pd.read_csv(csv_path)
        self.processed_data = None

    def preprocess(self) -> pd.DataFrame:
        """Main preprocessing pipeline."""
        df = self.raw_data.copy()
        
        # Filter only running activities
        df = df[df['sport_type'] == 'Run']
        
        # Convert date columns to datetime
        df['start_date'] = pd.to_datetime(df['start_date_local'])
        
        # Extract basic features
        df['distance_km'] = df['distance'].astype(float) / 1000
        df['duration_minutes'] = df['moving_time'].astype(float) / 60
        df['pace_min_km'] = df['duration_minutes'] / df['distance_km']
        df['speed_kmh'] = pace_to_speed(df['pace_min_km'])
        
        # Calculate heart rate features where available
        df['avg_heart_rate'] = pd.to_numeric(df['average_heartrate'], errors='coerce')
        df['max_heart_rate'] = pd.to_numeric(df['max_heartrate'], errors='coerce')
        df['heart_rate_reserve_used'] = (df['avg_heart_rate'] - 51) / (195 - 51)
        
        # Calculate Training Impulse
        df['training_impulse'] = pd.to_numeric(df['suffer_score'], errors='coerce') * 1.3
        
        # Extract elevation and intensity features
        df['elevation_gain'] = pd.to_numeric(df['total_elevation_gain'], errors='coerce')
        df['elevation_per_km'] = df['elevation_gain'] / df['distance_km']
        
        # Add time-based features
        df['day_of_week'] = df['start_date'].dt.dayofweek
        df['month'] = df['start_date'].dt.month
        df['year'] = df['start_date'].dt.year
        
        # Calculate rolling statistics
        df = df.sort_values('start_date')
        windows = [7, 14, 30, 90]
        for window in windows:
            df[f'rolling_{window}d_distance'] = df.rolling(
                window=f'{window}D', on='start_date')['distance_km'].sum()
            df[f'rolling_{window}d_runs'] = df.rolling(
                window=f'{window}D', on='start_date')['distance_km'].count()
            df[f'rolling_{window}d_avg_pace'] = df.rolling(
                window=f'{window}D', on='start_date')['pace_min_km'].mean()
            df[f'rolling_{window}d_load'] = df.rolling(
                window=f'{window}D', on='start_date')['distance_km'].apply(
                lambda x: np.sum(x * np.exp(-np.arange(len(x))/7))
            )
        
        # Days since last run
        df['days_since_last_run'] = df['start_date'].diff().dt.total_seconds() / (24 * 3600)
        
        # Select only relevant columns
        columns_to_keep = [
            # Time and date
            'start_date',
            'day_of_week',
            'month',
            'year',
            
            # Basic metrics
            'distance_km',
            'duration_minutes',
            'pace_min_km',
            'speed_kmh',
            
            # Heart rate and intensity
            'avg_heart_rate',
            'max_heart_rate',
            'heart_rate_reserve_used',
            'training_impulse',
            
            # Elevation
            'elevation_gain',
            'elevation_per_km',
            
            # Rolling statistics
            'rolling_7d_distance',
            'rolling_14d_distance',
            'rolling_30d_distance',
            'rolling_90d_distance',
            'rolling_7d_runs',
            'rolling_14d_runs',
            'rolling_30d_runs',
            'rolling_90d_runs',
            'rolling_7d_avg_pace',
            'rolling_14d_avg_pace',
            'rolling_30d_avg_pace',
            'rolling_90d_avg_pace',
            'rolling_7d_load',
            'rolling_14d_load',
            'rolling_30d_load',
            'rolling_90d_load',
            
            # Training consistency
            'days_since_last_run'
        ]
        
        df = df[columns_to_keep]
        
        # Store processed data
        self.processed_data = df
        
        return df

    def get_training_features(self, target_date: datetime, lookback_days: int = 90) -> Optional[pd.DataFrame]:
        """Extract training features for a specific date."""
        if self.processed_data is None:
            raise ValueError("Data must be preprocessed first")
            
        # Convert target_date to UTC timezone-aware datetime
        target_date = pd.to_datetime(target_date).tz_localize('UTC')
        cutoff_date = target_date - pd.Timedelta(days=lookback_days)
        
        mask = (self.processed_data['start_date'] <= target_date) & \
               (self.processed_data['start_date'] > cutoff_date)
               
        training_data = self.processed_data[mask].copy()
        
        if len(training_data) == 0:
            return None
            
        # Calculate comprehensive training features
        features = {
            # Volume metrics
            'total_distance': training_data['distance_km'].sum(),
            'avg_weekly_distance': training_data['distance_km'].sum() * 7 / lookback_days,
            'num_runs': len(training_data),
            'max_distance': training_data['distance_km'].max(),
            
            # Pace metrics
            'avg_pace': training_data['pace_min_km'].mean(),
            'best_pace': training_data['pace_min_km'].min(),
            'pace_std': training_data['pace_min_km'].std(),
            
            # Recent training load
            'recent_7d_distance': training_data['rolling_7d_distance'].iloc[-1],
            'recent_30d_distance': training_data['rolling_30d_distance'].iloc[-1],
            'recent_7d_load': training_data['rolling_7d_load'].iloc[-1],
            'recent_30d_load': training_data['rolling_30d_load'].iloc[-1],
            
            # Intensity metrics
            'avg_heart_rate': training_data['avg_heart_rate'].mean(),
            'max_heart_rate_session': training_data['max_heart_rate'].max(),
            'avg_hr_reserve_used': training_data['heart_rate_reserve_used'].mean(),
            
            # Elevation metrics
            'total_elevation': training_data['elevation_gain'].sum(),
            'avg_elevation_per_km': training_data['elevation_per_km'].mean(),
            
            # Consistency metrics
            'avg_days_between_runs': training_data['days_since_last_run'].mean(),
            'longest_break': training_data['days_since_last_run'].max(),
            
            # Time-based metrics
            'days_in_training': (training_data['start_date'].max() - 
                               training_data['start_date'].min()).days
        }
        
        return pd.DataFrame([features])

    def get_race_relevant_runs(self, target_distance: float, tolerance: float = 0.1) -> pd.DataFrame:
        """Get historical runs that are close to the target race distance."""
        if self.processed_data is None:
            raise ValueError("Data must be preprocessed first")
            
        distance_lower = target_distance * (1 - tolerance)
        distance_upper = target_distance * (1 + tolerance)
        
        mask = (self.processed_data['distance_km'] >= distance_lower) & \
               (self.processed_data['distance_km'] <= distance_upper)
               
        relevant_runs = self.processed_data[mask].copy()
        
        # Add race-specific features
        relevant_runs['relative_performance'] = (
            relevant_runs['pace_min_km'] / 
            relevant_runs['rolling_30d_avg_pace']
        )
        
        return relevant_runs.sort_values('pace_min_km')

