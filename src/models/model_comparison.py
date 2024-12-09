import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

class ModelComparison:
    def __init__(self):
        self.models = {
            'Linear Regression': LinearRegression(),
            'Ridge Regression': Ridge(alpha=1.0),
            'Random Forest': RandomForestRegressor(
                n_estimators=50,
                max_depth=5,
                min_samples_leaf=3,
                random_state=42
            ),
            'XGBoost': XGBRegressor(
                n_estimators=50,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        }
        self.scaler = StandardScaler()
        self.features = [
            'pace_min_km',
            'rolling_7d_distance',
            'distance_km',
            'duration_minutes'
        ]
        self.results = {}
        
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
    
    def train_and_evaluate(self, df: pd.DataFrame) -> dict:
        """Train all models and return performance metrics."""
        # Prepare data
        X_train_scaled, X_test_scaled, y_train, y_test = self.prepare_data(df)
        
        for name, model in self.models.items():
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred_train = model.predict(X_train_scaled)
            y_pred_test = model.predict(X_test_scaled)
            
            # Calculate metrics
            metrics = {
                'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
                'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
                'train_r2': r2_score(y_train, y_pred_train),
                'test_r2': r2_score(y_test, y_pred_test)
            }
            
            # Get feature importance if available
            if hasattr(model, 'coef_'):
                metrics['feature_importance'] = dict(zip(self.features, model.coef_))
            elif hasattr(model, 'feature_importances_'):
                metrics['feature_importance'] = dict(zip(self.features, model.feature_importances_))
            
            self.results[name] = metrics
        
        return self.results
    
    def plot_comparison(self):
        """Plot performance comparison of all models."""
        if not self.results:
            raise ValueError("Must train models before plotting comparison")
        
        metrics = ['train_rmse', 'test_rmse', 'train_r2', 'test_r2']
        fig, axes = plt.subplots(2, 1, figsize=(10, 12))
        
        # Plot RMSE
        x = np.arange(len(self.models))
        width = 0.35
        
        train_rmse = [self.results[model]['train_rmse'] for model in self.models]
        test_rmse = [self.results[model]['test_rmse'] for model in self.models]
        
        axes[0].bar(x - width/2, train_rmse, width, label='Train RMSE')
        axes[0].bar(x + width/2, test_rmse, width, label='Test RMSE')
        axes[0].set_ylabel('RMSE (bpm)')
        axes[0].set_title('RMSE Comparison')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(self.models.keys())
        axes[0].legend()
        
        # Plot R²
        train_r2 = [self.results[model]['train_r2'] for model in self.models]
        test_r2 = [self.results[model]['test_r2'] for model in self.models]
        
        axes[1].bar(x - width/2, train_r2, width, label='Train R²')
        axes[1].bar(x + width/2, test_r2, width, label='Test R²')
        axes[1].set_ylabel('R²')
        axes[1].set_title('R² Comparison')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(self.models.keys())
        axes[1].legend()
        
        plt.tight_layout()
        plt.show() 