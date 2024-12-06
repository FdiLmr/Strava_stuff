from src.data_preprocessing.main import StravaDataPreprocessor
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

def main():
    # Initialize preprocessor with your latest data file
    data_file = 'data/my_activity_data=20241206180702.csv'
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

    # Print some basic statistics
    print("Basic Statistics:")
    print(f"Total runs: {len(processed_data)}")
    print(f"Date range: {processed_data['start_date'].min()} to {processed_data['start_date'].max()}")
    print(f"Average distance: {processed_data['distance_km'].mean():.2f} km")
    print(f"Average pace: {processed_data['pace_min_km'].mean():.2f} min/km\n")

    # Get training features for current date
    print("Recent Training Features:")
    current_date = datetime.now()
    training_features = preprocessor.get_training_features(current_date)
    if training_features is not None:
        for feature, value in training_features.iloc[0].items():
            if pd.notnull(value):  # Only print non-null values
                print(f"{feature}: {value:.2f}")
    print()

    # Look at some specific race distances
    distances = [5, 10, 21.1]  # 5K, 10K, Half Marathon
    for distance in distances:
        print(f"\nAnalyzing {distance}km runs:")
        relevant_runs = preprocessor.get_race_relevant_runs(distance)
        if len(relevant_runs) > 0:
            print(f"Found {len(relevant_runs)} similar runs")
            print("\nTop 3 performances:")
            top_3 = relevant_runs.head(3)[['start_date', 'distance_km', 'pace_min_km', 'relative_performance']]
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(top_3.to_string())
        else:
            print(f"No runs found close to {distance}km")

if __name__ == '__main__':
    main()
