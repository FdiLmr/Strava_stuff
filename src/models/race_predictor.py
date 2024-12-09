import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class RacePredictor:
    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.features = [
            'distance_km',
            'pace_min_km',
            'heart_rate_reserve_used',
            'training_impulse',
            'rolling_7d_distance',
            'rolling_30d_distance',
            'rolling_7d_avg_pace',
            'rolling_30d_avg_pace',
            'rolling_7d_load',
            'rolling_30d_load'
        ]
        
    def prepare_data(self, strava_data: pd.DataFrame, garmin_data: pd.DataFrame) -> tuple:
        """Prepare data for training by combining Strava and Garmin data."""
        # Clean up Garmin data - take the last prediction for each day
        garmin_daily = (garmin_data.sort_values('timestamp')
                       .groupby('calendarDate')
                       .last()
                       .reset_index())
        
        # Convert race times from seconds to minutes
        for col in ['raceTime5K', 'raceTime10K', 'raceTimeHalf', 'raceTimeMarathon']:
            garmin_daily[col] = garmin_daily[col] / 60
        
        # Get training features for each date in Garmin data
        training_features = []
        for date in garmin_daily['calendarDate']:
            # Convert to datetime without timezone first
            date = pd.to_datetime(date)
            features = self._get_training_features(strava_data, date)
            if features is not None:
                training_features.append(features)
        
        training_df = pd.DataFrame(training_features)
        
        # Convert date back to string format for merging
        training_df['calendarDate'] = pd.to_datetime(training_df['date']).dt.strftime('%Y-%m-%d')
        full_data = training_df.merge(garmin_daily, on='calendarDate', how='inner')
        
        # Prepare features and targets
        X = full_data[self.features]
        y = full_data[['raceTime5K', 'raceTime10K', 'raceTimeHalf', 'raceTimeMarathon']]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def _get_training_features(self, df: pd.DataFrame, target_date: datetime) -> dict:
        """Extract training features for a specific date."""
        df = df.copy()
        
        # Convert target_date to UTC timezone-aware datetime
        target_date = pd.to_datetime(target_date).tz_localize('UTC')
        cutoff_date = target_date - timedelta(days=90)
        
        mask = (df['start_date'] <= target_date) & (df['start_date'] > cutoff_date)
        training_data = df[mask]
        
        if len(training_data) == 0:
            return None
        
        features = {
            'date': target_date,
            'distance_km': training_data['distance_km'].mean(),
            'pace_min_km': training_data['pace_min_km'].mean(),
            'heart_rate_reserve_used': training_data['heart_rate_reserve_used'].mean(),
            'training_impulse': training_data['training_impulse'].mean(),
            'rolling_7d_distance': training_data['rolling_7d_distance'].iloc[-1],
            'rolling_30d_distance': training_data['rolling_30d_distance'].iloc[-1],
            'rolling_7d_avg_pace': training_data['rolling_7d_avg_pace'].iloc[-1],
            'rolling_30d_avg_pace': training_data['rolling_30d_avg_pace'].iloc[-1],
            'rolling_7d_load': training_data['rolling_7d_load'].iloc[-1],
            'rolling_30d_load': training_data['rolling_30d_load'].iloc[-1]
        }
        
        return features
    
    def train(self, X_train: np.ndarray, y_train: pd.DataFrame) -> dict:
        """Train models for each race distance."""
        self.models = {}
        metrics = {}
        
        for distance in ['5K', '10K', 'Half', 'Marathon']:
            col = f'raceTime{distance}'
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            model.fit(X_train, y_train[col])
            self.models[distance] = model
        
        return metrics
    
    def evaluate(self, X_test: np.ndarray, y_test: pd.DataFrame) -> dict:
        """Evaluate models on test data."""
        results = {}
        
        for distance, model in self.models.items():
            col = f'raceTime{distance}'
            y_pred = model.predict(X_test)
            
            results[distance] = {
                'rmse': np.sqrt(mean_squared_error(y_test[col], y_pred)),
                'r2': r2_score(y_test[col], y_pred),
                'feature_importance': dict(zip(self.features, model.feature_importances_))
            }
        
        return results
    
    def plot_predictions(self, X_test: np.ndarray, y_test: pd.DataFrame):
        """Plot actual vs predicted times for each race distance."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        axes = axes.ravel()
        
        for idx, (distance, model) in enumerate(self.models.items()):
            col = f'raceTime{distance}'
            y_pred = model.predict(X_test)
            
            axes[idx].scatter(y_test[col], y_pred, alpha=0.5)
            axes[idx].plot([y_test[col].min(), y_test[col].max()],
                         [y_test[col].min(), y_test[col].max()],
                         'r--', lw=2)
            axes[idx].set_xlabel(f'Actual {distance} Time (minutes)')
            axes[idx].set_ylabel(f'Predicted {distance} Time (minutes)')
            axes[idx].set_title(f'{distance} Race Time Predictions')
        
        plt.tight_layout()
        plt.show() 