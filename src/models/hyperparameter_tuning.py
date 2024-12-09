import pandas as pd
import numpy as np
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, r2_score, make_scorer
import matplotlib.pyplot as plt

class ModelTuning:
    def __init__(self):
        self.rf_params = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 5, 7, 10],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
        
        self.xgb_params = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.05, 0.1],
            'subsample': [0.8, 0.9, 1.0],
            'colsample_bytree': [0.8, 0.9, 1.0]
        }
        
        self.features = [
            'pace_min_km',
            'rolling_7d_distance',
            'distance_km',
            'duration_minutes'
        ]
        
        self.scaler = StandardScaler()
        self.best_models = {}
        self.cv_results = {}
        
    def prepare_data(self, df: pd.DataFrame) -> tuple:
        """Prepare data for training/testing."""
        df = df.copy()
        df = df.dropna(subset=['avg_heart_rate'] + self.features)
        
        X = df[self.features]
        y = df['avg_heart_rate']
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled, y
    
    def tune_random_forest(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Tune Random Forest hyperparameters."""
        rf = RandomForestRegressor(random_state=42)
        
        # Create GridSearchCV object
        grid_search = GridSearchCV(
            estimator=rf,
            param_grid=self.rf_params,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=1
        )
        
        # Fit the model
        grid_search.fit(X, y)
        
        # Store results
        self.best_models['Random Forest'] = grid_search.best_estimator_
        self.cv_results['Random Forest'] = {
            'best_params': grid_search.best_params_,
            'best_score': grid_search.best_score_,
            'cv_results': pd.DataFrame(grid_search.cv_results_)
        }
        
        return self.cv_results['Random Forest']
    
    def tune_xgboost(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Tune XGBoost hyperparameters."""
        xgb = XGBRegressor(random_state=42)
        
        # Create GridSearchCV object
        grid_search = GridSearchCV(
            estimator=xgb,
            param_grid=self.xgb_params,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=1
        )
        
        # Fit the model
        grid_search.fit(X, y)
        
        # Store results
        self.best_models['XGBoost'] = grid_search.best_estimator_
        self.cv_results['XGBoost'] = {
            'best_params': grid_search.best_params_,
            'best_score': grid_search.best_score_,
            'cv_results': pd.DataFrame(grid_search.cv_results_)
        }
        
        return self.cv_results['XGBoost']
    
    def plot_param_importance(self, model_name: str):
        """Plot importance of different parameters."""
        if model_name not in self.cv_results:
            raise ValueError(f"No results found for {model_name}")
            
        results = self.cv_results[model_name]['cv_results']
        params = self.rf_params if model_name == 'Random Forest' else self.xgb_params
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        axes = axes.ravel()
        
        for idx, (param_name, param_values) in enumerate(params.items()):
            if idx < 4:  # Plot only first 4 parameters if more exist
                # Calculate mean score for each parameter value
                param_scores = []
                for value in param_values:
                    mask = results[f'param_{param_name}'].astype(str) == str(value)
                    mean_score = results.loc[mask, 'mean_test_score'].mean()
                    param_scores.append(mean_score)
                
                axes[idx].plot(param_values, param_scores, 'o-')
                axes[idx].set_xlabel(param_name)
                axes[idx].set_ylabel('Mean CV Score (R²)')
                axes[idx].set_title(f'Impact of {param_name}')
        
        plt.tight_layout()
        plt.show() 