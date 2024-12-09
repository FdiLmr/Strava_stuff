from src.data_preprocessing.main import StravaDataPreprocessor
from src.fetch_strava_data import fetch_strava_data
from src.models.race_predictor import RacePredictor
from datetime import datetime
import pandas as pd
from pathlib import Path

def main():
    fetch_strava_data()

    # Load and preprocess Strava data
    strava_file = 'data/my_activity_data=20241209224822.csv'
    print(f"Loading Strava data from: {strava_file}")
    preprocessor = StravaDataPreprocessor(strava_file)
    strava_data = preprocessor.preprocess()
    
    # Load Garmin predictions
    garmin_file = 'data/Garmin_data/Garmin_RunRacePredictions_20240418_20250212.csv'
    print(f"Loading Garmin data from: {garmin_file}")
    garmin_data = pd.read_csv(garmin_file)
    
    # Initialize and train race predictor
    print("\nTraining Race Prediction Models...")
    predictor = RacePredictor()
    X_train, X_test, y_train, y_test = predictor.prepare_data(strava_data, garmin_data)
    
    predictor.train(X_train, y_train)
    results = predictor.evaluate(X_test, y_test)
    
    # Print results
    for distance, metrics in results.items():
        print(f"\n{distance} Race Predictions:")
        print(f"RMSE: {metrics['rmse']:.2f} minutes")
        print(f"R²: {metrics['r2']:.3f}")
        print("\nFeature Importance:")
        for feature, importance in sorted(
            metrics['feature_importance'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            print(f"{feature}: {importance:.3f}")
    
    # Plot predictions
    predictor.plot_predictions(X_test, y_test)

if __name__ == '__main__':
    main()
