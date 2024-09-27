from datetime import datetime
from pathlib import Path

from src.api_methods import get_methods
from src.api_methods import authorize
from src.data_preprocessing import main as data_prep
import pandas as pd

# Maximum number of activities per page
ACTIVITIES_PER_PAGE = 200

def main():
    token = authorize.get_acces_token()
    all_data = []  # List to store all activity data
    page = 1  # Start from the first page

    while True:
        print(f"Fetching page {page}")
        params = {
            'per_page': ACTIVITIES_PER_PAGE,
            'page': page
        }
        data = get_methods.access_activity_data(token, params=params)
        
        if not data:
            # No more data returned from the API
            print("No more activities to fetch.")
            break

        all_data.extend(data)
        page += 1  # Move to the next page

    # Preprocess and save the data
    df = data_prep.preprocess_data(all_data)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    df.to_csv(Path('data', f'my_activity_data={timestamp}.csv'), index=False)
    print(f"Total activities fetched: {len(df)}")

if __name__ == '__main__':
    main()
