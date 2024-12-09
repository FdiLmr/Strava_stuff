import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

class HeartRatePredictor:
    def __init__(self):
        # Reduce complexity with max_depth and fewer trees
        self.model = RandomForestRegressor(
            n_estimators=50,  # Reduced from 100
            max_depth=5,      # Limit tree depth
            min_samples_leaf=3,  # Require more samples per leaf
            random_state=42
        )
        self.scaler = StandardScaler()
        # Keep only the most important features
        self.features = [
            'pace_min_km',
            'rolling_7d_distance',
            'distance_km',
            'duration_minutes'
        ]
        
    def prepare_data(self, df: pd.DataFrame) -> tuple:
        """Prepare data for training/testing."""
        df = df.copy()
        
        # Drop rows with missing heart rate values
        df = df.dropna(subset=['avg_heart_rate'] + self.features)
        
        X = df[self.features]
        y = df['avg_heart_rate']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def train(self, df: pd.DataFrame) -> dict:
        """Train the model and return performance metrics."""
        # Prepare data
        X_train_scaled, X_test_scaled, y_train, y_test = self.prepare_data(df)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Make predictions
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        metrics = {
            'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
            'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
            'train_r2': r2_score(y_train, y_pred_train),
            'test_r2': r2_score(y_test, y_pred_test),
            'feature_importance': dict(zip(self.features, self.model.feature_importances_))
        }
        
        return metrics
    
    def plot_predictions(self, df: pd.DataFrame):
        """Plot actual vs predicted heart rates."""
        X_train_scaled, X_test_scaled, y_train, y_test = self.prepare_data(df)
        y_pred_test = self.model.predict(X_test_scaled)
        
        plt.figure(figsize=(10, 6))
        plt.scatter(y_test, y_pred_test, alpha=0.5)
        plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
        plt.xlabel('Actual Heart Rate')
        plt.ylabel('Predicted Heart Rate')
        plt.title('Actual vs Predicted Heart Rate')
        plt.tight_layout()
        plt.show()
    
    def predict(self, distance: float, duration: float, pace: float, rolling_distance: float) -> float:
        """Predict heart rate for new input."""
        if not hasattr(self.model, 'feature_importances_'):
            raise ValueError("Model must be trained before making predictions")
            
        # Scale input
        X_new = np.array([[pace, rolling_distance, distance, duration]])
        X_new_scaled = self.scaler.transform(X_new)
        
        # Make prediction
        prediction = self.model.predict(X_new_scaled)[0]
        
        return prediction 