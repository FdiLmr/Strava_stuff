import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

class RacePredictor:
    def __init__(self, data_path='data/activities.csv'):
        """Initialize the race predictor with path to activities data."""
        self.data_path = data_path
        self.model = None
        self.scaler = StandardScaler()
        
    def load_and_preprocess_data(self):
        """Load and preprocess the Strava activities data."""
        # Load data
        print("Loading data from:", self.data_path)
        df = pd.read_csv(self.data_path)
        print(f"Loaded {len(df)} activities")
        
        # Convert date column by first replacing French month abbreviations
        print("Converting dates...")
        month_map = {
            'janv.': 'Jan',
            'févr.': 'Feb',
            'mars': 'Mar',
            'avr.': 'Apr',
            'mai': 'May',
            'juin': 'Jun',
            'juil.': 'Jul',
            'août': 'Aug',
            'sept.': 'Sep',
            'oct.': 'Oct',
            'nov.': 'Nov',
            'déc.': 'Dec'
        }
        
        # Replace French month abbreviations with English ones
        date_series = df['Date de l\'activité'].copy()
        for fr_month, en_month in month_map.items():
            date_series = date_series.str.replace(fr_month, en_month)
        
        # Convert to datetime
        df['date'] = pd.to_datetime(date_series, format='%d %b %Y à %H:%M:%S')
        
        # Filter for running activities only
        print("Filtering running activities...")
        df = df[df['Type d\'activité'] == 'Course à pied']
        print(f"Found {len(df)} running activities")
        
        # Clean and convert distance and time columns
        print("Converting distance and time...")
        df['distance'] = pd.to_numeric(df['Distance'].str.replace(',', '.'), errors='coerce')
        df['moving_time'] = pd.to_numeric(df['Durée de déplacement'], errors='coerce')
        
        # Calculate pace (minutes per km)
        print("Calculating pace...")
        df['pace'] = df['moving_time'] / 60 / df['distance']
        print(f"Pace range: {df['pace'].min():.2f} - {df['pace'].max():.2f} min/km")
        
        # Convert heart rate if available
        if 'Fréquence cardiaque moyenne' in df.columns:
            df['avg_hr'] = pd.to_numeric(df['Fréquence cardiaque moyenne'], errors='coerce')
            print("Added heart rate data")
        
        # Convert elevation if available
        if 'Dénivelé positif' in df.columns:
            df['elevation_gain'] = pd.to_numeric(df['Dénivelé positif'], errors='coerce')
            print("Added elevation data")
        
        # Sort by date
        df = df.sort_values('date')
        
        # Remove outliers (extremely slow or fast paces)
        print("\nRemoving outliers...")
        before_outliers = len(df)
        df = df[df['pace'].between(df['pace'].quantile(0.05), df['pace'].quantile(0.95))]
        print(f"Removed {before_outliers - len(df)} outlier activities")
        
        self.data = df
        print(f"\nFinal dataset: {len(df)} activities")
        return df
    
    def create_features(self, window_sizes=[7, 14, 30, 90]):
        """Create training features from running history."""
        df = self.data.copy()
        
        # Create a date-indexed DataFrame for rolling calculations
        df_dated = df.set_index('date')
        
        # Initialize features DataFrame with the same index as the input data
        features = pd.DataFrame(index=df.index)
        
        # Add base features
        features['pace'] = df['pace']
        features['distance'] = df['distance']
        
        for window in window_sizes:
            # Calculate rolling averages on the date-indexed data
            window_days = f'{window}D'
            
            # Calculate rolling stats on the date-indexed data
            rolling_stats = df_dated.rolling(window_days, min_periods=1)
            
            # Training volume features
            features[f'distance_{window}d_avg'] = rolling_stats['distance'].mean().values
            features[f'runs_{window}d_count'] = rolling_stats['distance'].count().values
            
            # Performance features
            features[f'pace_{window}d_avg'] = rolling_stats['pace'].mean().values
            features[f'pace_{window}d_min'] = rolling_stats['pace'].min().values
            
            # Training load features
            if 'avg_hr' in df.columns:
                features[f'hr_{window}d_avg'] = rolling_stats['avg_hr'].mean().values
            
            # Elevation features
            if 'elevation_gain' in df.columns:
                features[f'elevation_{window}d_total'] = rolling_stats['elevation_gain'].sum().values
        
        # Add target distance as a feature
        features['target_distance'] = df['distance']
        
        # Add seasonal features
        features['day_of_year'] = df['date'].dt.dayofyear
        features['day_of_week'] = df['date'].dt.dayofweek
        
        # Fill any remaining NaN values
        features = features.fillna(method='ffill').fillna(method='bfill')
        
        # Store features
        self.features = features
        
        return features
    
    def prepare_training_data(self, target_col='pace', test_size=0.2):
        """Prepare training and testing datasets."""
        features = self.features.copy()
        
        # Remove rows with NaN values
        features = features.dropna()
        
        # Split features and target
        X = features.drop([target_col], axis=1)
        y = features[target_col]
        
        # Split into training and testing sets (time-based)
        split_idx = int(len(features) * (1 - test_size))
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def train_model(self):
        """Train the prediction model."""
        X_train, X_test, y_train, y_test = self.prepare_training_data()
        
        # Initialize and train model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        train_pred = self.model.predict(X_train)
        test_pred = self.model.predict(X_test)
        
        train_mae = mean_absolute_error(y_train, train_pred)
        test_mae = mean_absolute_error(y_test, test_pred)
        
        print(f"Training MAE: {train_mae:.2f} min/km")
        print(f"Testing MAE: {test_mae:.2f} min/km")
        
        return train_mae, test_mae
    
    def predict_race_time(self, target_distance, recent_activities=None):
        """Predict race time for a target distance."""
        if recent_activities is None:
            recent_activities = self.data.tail(90)  # Use last 90 days of data
            
        # Create features for prediction
        pred_features = self.create_features()
        pred_features = pred_features.iloc[-1:].copy()  # Use most recent state
        pred_features['target_distance'] = target_distance
        
        # Scale features
        pred_features_scaled = self.scaler.transform(pred_features)
        
        # Predict pace
        predicted_pace = self.model.predict(pred_features_scaled)[0]
        
        # Calculate predicted time
        predicted_time_minutes = predicted_pace * target_distance
        
        # Convert to hours:minutes:seconds
        hours = int(predicted_time_minutes // 60)
        minutes = int(predicted_time_minutes % 60)
        seconds = int((predicted_time_minutes * 60) % 60)
        
        return {
            'predicted_pace': predicted_pace,
            'predicted_time': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            'predicted_time_minutes': predicted_time_minutes
        }
    
    def plot_pace_curve(self, distances=None):
        """Plot predicted pace curve across different distances."""
        if distances is None:
            distances = np.linspace(1, 42.2, 20)  # From 1km to marathon
            
        paces = []
        for dist in distances:
            pred = self.predict_race_time(dist)
            paces.append(pred['predicted_pace'])
            
        plt.figure(figsize=(12, 6))
        plt.plot(distances, paces, 'b-', label='Predicted Pace')
        plt.scatter(self.data['distance'], self.data['pace'], 
                   alpha=0.3, label='Actual Runs')
        
        plt.xlabel('Distance (km)')
        plt.ylabel('Pace (min/km)')
        plt.title('Predicted Race Pace vs Distance')
        plt.legend()
        plt.grid(True)
        plt.savefig('pace_prediction_curve.png')
        return plt.gcf()

def main():
    # Initialize predictor
    predictor = RacePredictor()
    
    # Load and preprocess data
    print("Loading and preprocessing data...")
    predictor.load_and_preprocess_data()
    
    # Create features and train model
    print("\nTraining model...")
    predictor.create_features()
    predictor.train_model()
    
    # Example predictions
    target_distances = [5, 10, 21.1, 42.2]  # 5K, 10K, Half Marathon, Marathon
    
    print("\nRace Predictions:")
    print("-" * 50)
    for distance in target_distances:
        prediction = predictor.predict_race_time(distance)
        print(f"\nDistance: {distance}km")
        print(f"Predicted Pace: {prediction['predicted_pace']:.2f} min/km")
        print(f"Predicted Time: {prediction['predicted_time']}")
    
    # Plot pace curve
    print("\nGenerating pace prediction curve...")
    predictor.plot_pace_curve()
    print("Pace prediction curve saved as 'pace_prediction_curve.png'")

if __name__ == "__main__":
    main() 