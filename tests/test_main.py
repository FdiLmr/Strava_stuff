# tests/test_main.py

import pytest
from second_part.main import app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    """Flask test client for the main app."""
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Check that the index page returns 200."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<title>Strava Integration</title>" not in resp.data  # or some known text

def test_login_route(client):
    """Check that the /login endpoint redirects to Strava's OAuth."""
    with patch("app.main.authorize_url", return_value="http://fake-authorize-url"):
        resp = client.get("/login")
        assert resp.status_code == 302
        assert resp.location == "http://fake-authorize-url"

@patch("app.main.refresh_tokens")
def test_update_tokens_route(mock_refresh_tokens, client):
    """Test that /update_tokens calls the refresh_tokens function."""
    mock_refresh_tokens.return_value = 0
    resp = client.get("/update_tokens")
    assert resp.status_code == 200
    assert b"0" in resp.data
    mock_refresh_tokens.assert_called_once()

@patch("app.main.fetch_strava_data")
def test_fetch_strava_data_route(mock_fetch, client):
    """Test that /fetch_strava_data calls fetch_strava_data."""
    mock_fetch.return_value = "Mock fetch complete"
    resp = client.get("/fetch_strava_data")
    assert resp.status_code == 200
    assert b"Mock fetch complete" in resp.data
    mock_fetch.assert_called_once()

@patch("app.main.process_stored_data")
def test_process_stored_data_route(mock_process, client):
    """Test that /process_stored_data calls process_stored_data."""
    mock_process.return_value = "Mock processing complete"
    resp = client.get("/process_stored_data")
    assert resp.status_code == 200
    assert b"Mock processing complete" in resp.data
    mock_process.assert_called_once()
