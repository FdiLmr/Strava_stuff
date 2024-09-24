# Strava Stuff

## Project Overview

This project is centered around interacting with the Strava API to access and analyze personal fitness data. Here's what has been accomplished so far:

1. **API Authentication Setup**: 
   - Obtained necessary credentials (Client ID and Client Secret) from the Strava API.
   - Implemented the OAuth 2.0 flow to authenticate and authorize access to Strava data.
   - Successfully retrieved and stored the refresh token for ongoing API access.

2. **Environment Configuration**:
   - Created a `.env` file to securely store sensitive information like Client ID, Client Secret, and Refresh Token.
   - Set up a `.gitignore` file to prevent committing sensitive data and unnecessary files to the repository.

3. **Initial API Integration**:
   - Established the groundwork for making API calls to Strava using the obtained credentials.

## Next Steps

The project is currently at an exploratory stage. The immediate plans involve:

1. **Data Retrieval**: Implementing functions to fetch various types of activity data from Strava.
2. **Data Analysis**: Exploring the retrieved data to identify interesting patterns or insights.
3. **Potential Directions**:
   - Visualizing activity trends over time
   - Analyzing performance metrics across different activity types
   - Identifying correlations between various factors (e.g., weather, time of day) and performance
   - Creating a personal fitness dashboard

The ultimate goal is to leverage this Strava data to gain meaningful insights into personal fitness habits and potentially discover areas for improvement or interesting trends in athletic performance.

As the project evolves, this README will be updated to reflect new developments and findings.
