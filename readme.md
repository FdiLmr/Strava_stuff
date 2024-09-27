# Strava Running Analysis

This project analyzes personal running data from Strava to calculate Personal Records (PRs), visualize performance, and track progress over time.

## Features

1. **Data Retrieval**: Fetches running activity data from Strava using their API.
2. **Personal Records (PRs) Calculation**: Identifies best times over standard distances, considering all sub-runs within longer runs.
3. **PR Visualization**: Plots best pace against distance for a comprehensive view of performance across different distances.
4. **Animated PR History**: Creates an animated GIF showing how PRs have evolved over time.
5. **Detailed GPS Analysis**: Processes detailed GPS data to compute accurate paces for sub-sections of runs.
6. **Best Pace Curve**: Generates a curve showing the best achieved pace for every distance.
7. **Individual Run Comparison**: Allows comparison of specific runs against the all-time PR curve.

## Implementation Details

- Uses Python with libraries such as pandas, numpy, matplotlib, and requests.
- Implements efficient algorithms to calculate best paces over various distances.
- Utilizes the Strava API to fetch detailed activity data and streams.
- Employs data caching to minimize API calls and respect rate limits.

## Key Components

1. **Data Fetching**: 
   - Retrieves activity data and detailed GPS streams from Strava.
   - Implements token refresh mechanism for API authentication.

2. **Data Processing**:
   - Calculates pace and other metrics from raw activity data.
   - Processes GPS streams to compute accurate sub-run performances.

3. **PR Calculation**:
   - Implements algorithms to efficiently find best performances across all possible distances.

4. **Visualization**:
   - Creates static plots for PR curves and pace vs. distance relationships.
   - Generates animated visualizations to show PR progression over time.

5. **Analysis Tools**:
   - Provides functions to analyze individual runs and compare them to overall PRs.
   - Implements logarithmic regression for trend analysis in pace vs. distance curves.

## Usage

[Include instructions on how to set up and run the project, including any required API keys or data files]

## Future Improvements

- Enhance the efficiency of PR calculations for larger datasets.
- Implement more advanced statistical analysis of running performance.
- Add features to automatically update Strava activity descriptions with insights.

## Dependencies

- pandas
- numpy
- matplotlib
- requests
- tqdm
- imageio
- scipy

## Note

This project respects Strava's API usage guidelines and implements rate limiting to avoid excessive API calls.

