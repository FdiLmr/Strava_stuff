# tests/test_update_data.py

import pytest
import json
import pandas as pd
from unittest.mock import patch, MagicMock
from second_part.update_data import (
    refresh_tokens,
    fetch_strava_data,
    get_unprocessed_activities,
    save_activity_data
)

@pytest.fixture
def mock_requests_post():
    """Fixture that returns a MagicMock for requests.post."""
    with patch("requests.post") as mock_post:
        yield mock_post

@pytest.fixture
def mock_requests_get():
    """Fixture that returns a MagicMock for requests.get."""
    with patch("requests.get") as mock_get:
        yield mock_get

def test_get_unprocessed_activities():
    # Suppose these are existing activity IDs
    existing_ids = {1001, 1002}
    activity_list = [
        {"id": 1001, "name": "Old Activity"},
        {"id": 2001, "name": "New Activity"},
        {"id": 2002, "name": "Another New Activity"},
    ]
    # Should pick up only 2 unprocessed activities if limit=2
    unprocessed = get_unprocessed_activities(activity_list, existing_ids, limit=2)
    assert len(unprocessed) == 2
    assert unprocessed[0]["id"] == 2001
    assert unprocessed[1]["id"] == 2002

def test_save_activity_data(tmp_path):
    """Test saving JSON data to a file."""
    athlete_id = 123
    activities = [{"id": 1111, "name": "Test Activity"}]
    timestamp = "testtimestamp"
    
    # Use tmp_path so we don't write to real disk
    # Patch the data dir inside the function to our tmp_path
    with patch("app.update_data.os.path.exists", return_value=False), \
         patch("app.update_data.os.makedirs") as mock_makedirs, \
         patch("app.update_data.open", new_callable=pytest.mock.mock_open()) as mock_file:
        
        save_activity_data(athlete_id, activities, timestamp)
        
        # Check if the directory was created
        mock_makedirs.assert_called_once()
        # Check if the file was written correctly
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        assert json.loads(written_content)[timestamp] == activities

def test_refresh_tokens(mock_requests_post):
    """Test token refresh logic, ensuring the DB is updated."""
    # Mock return data from Strava token refresh
    fake_json = {
        "access_token": "fake_access_token",
        "refresh_token": "fake_refresh_token",
    }
    # Configure mock to return success
    mock_response = MagicMock()
    mock_response.json.return_value = fake_json
    mock_requests_post.return_value = mock_response
    
    # Patch read_db/write_db_replace to avoid real DB calls
    with patch("app.update_data.read_db", return_value=pd.DataFrame({
        "athlete_id": [42],
        "status": ["none"],
        "refresh_token": ["old_token"],
        "bearer_token": [None],
    })), patch("app.update_data.write_db_replace") as mock_write:
        result = refresh_tokens()
        assert result == 0  # Means success
        # Check the updated DataFrame
        updated_df = mock_write.call_args[0][0]
        assert updated_df.at[0, "bearer_token"] == "fake_access_token"
        assert updated_df.at[0, "refresh_token"] == "fake_refresh_token"

@pytest.mark.parametrize("api_calls", [0, 25001])
def test_fetch_strava_data_rate_limit(api_calls, mock_requests_get):
    """Test the fetch_strava_data function for handling rate limits."""
    # For testing, let's mock the daily_limit
    daily_limit_df = pd.DataFrame({"daily": [api_calls]})
    with patch("app.update_data.read_db", side_effect=[daily_limit_df, pd.DataFrame(), pd.DataFrame()]), \
         patch("app.update_data.write_db_replace"), \
         patch("app.update_data.db"):

        if api_calls > 25000:
            # Expect a limit-exceeded message
            result = fetch_strava_data()
            assert "api limit exceeded" in result
        else:
            # We won't fully mock everything in fetch_strava_data,
            # but you could if you want a more thorough test.
            # Just check that we don't get the limit error here.
            result = fetch_strava_data()
            assert "api limit exceeded" not in result
