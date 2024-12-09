from src.data_preprocessing.main import StravaDataPreprocessor
from src.fetch_strava_data import fetch_strava_data
from src.models.model_comparison import ModelComparison
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

def main():
    fetch_strava_data()

    # Initialize preprocessor with your latest data file
    data_file = 'data/my_activity_data=20241209224822.csv'
    print(f"Attempting to read from: {data_file}")
    preprocessor = StravaDataPreprocessor(data_file)

    # Preprocess the data
    print("Preprocessing data...")
    processed_data = preprocessor.preprocess()
    print(f"Processed {len(processed_data)} activities\n")

    # Save preprocessed data
    output_dir = Path('data/processed')
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f'processed_activities_{timestamp}.csv'
    processed_data.to_csv(output_file, index=False)
    print(f"Saved preprocessed data to: {output_file}\n")

    # Print basic statistics
    print("Basic Statistics:")
    print(f"Total runs: {len(processed_data)}")
    print(f"Date range: {processed_data['start_date'].min()} to {processed_data['start_date'].max()}")
    print(f"Average distance: {processed_data['distance_km'].mean():.2f} km")
    print(f"Average pace: {processed_data['pace_min_km'].mean():.2f} min/km\n")

    # Compare different models
    print("\nComparing Different Models...")
    model_comparison = ModelComparison()
    results = model_comparison.train_and_evaluate(processed_data)
    
    # Print results for each model
    for model_name, metrics in results.items():
        print(f"\n{model_name} Performance:")
        print(f"Training RMSE: {metrics['train_rmse']:.2f} bpm")
        print(f"Test RMSE: {metrics['test_rmse']:.2f} bpm")
        print(f"Training R²: {metrics['train_r2']:.3f}")
        print(f"Test R²: {metrics['test_r2']:.3f}")
        
        if 'feature_importance' in metrics:
            print("\nFeature Importance:")
            for feature, importance in metrics['feature_importance'].items():
                print(f"{feature}: {importance:.3f}")
    
    # Plot comparison
    model_comparison.plot_comparison()

if __name__ == '__main__':
    main()
