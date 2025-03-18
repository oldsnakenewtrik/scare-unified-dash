# SCARE Unified Metrics Dashboard

A comprehensive dashboard for aggregating and visualizing marketing metrics from multiple sources including RedTrack, Google Ads, Bing Ads, Salesforce, and Matomo.

## Project Overview

This project implements a unified metrics dashboard that consolidates data from various marketing platforms, providing a centralized view of campaign performance across different channels.

### Features

- **Unified Campaign View**: View all campaign metrics in one place with monthly tabs
- **Toggle Active/Archived Campaigns**: Filter to show only active campaigns or include archived ones
- **Sort and Filter**: Sort by any metric column and filter by time period
- **Data Aggregation**: Automatically aggregates data from multiple sources
- **Historical Data Backfill**: Easily backfill historical data from Google Ads and Bing Ads
- **Dockerized Deployment**: Easy deployment using Docker and Railway

## Architecture

The project follows a microservices architecture:

- **API Service**: FastAPI-based backend for data retrieval and aggregation
- **Data Ingestion Services**: Separate services for each data source
  - RedTrack Connector
  - Google Ads Connector
  - Bing Ads Connector
  - Salesforce Email Connector
- **Database**: PostgreSQL for data storage
- **Frontend**: React-based dashboard with Material UI

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js (for local development)
- Python 3.9+ (for local development)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/scare-unified-dash.git
   cd scare-unified-dash
   ```

2. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```
   Edit the `.env` file to add your API keys and configurations.

3. Start the application using Docker Compose:
   ```
   docker-compose up -d
   ```

4. Access the dashboard at http://localhost:3000

### Development

For development, you can run the services individually:

```
# API Service
cd src/api
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd src/frontend
npm install
npm start
```

### Data Backfill

The system includes a backfill script to populate historical data from Google Ads and Bing Ads:

```
# Backfill both Google Ads and Bing Ads for a specific date range
python backfill.py --start-date 2024-01-01 --end-date 2024-03-31

# Backfill only Google Ads
python backfill.py --start-date 2024-01-01 --end-date 2024-03-31 --source google

# Backfill only Bing Ads
python backfill.py --start-date 2024-01-01 --end-date 2024-03-31 --source bing
```

You can also run backfill commands directly in the containers:

```
# Google Ads backfill
docker-compose run --rm google_ads python /app/main.py --backfill --start-date 2024-01-01 --end-date 2024-03-31

# Bing Ads backfill
docker-compose run --rm bing_ads python /app/main.py --backfill --start-date 2024-01-01 --end-date 2024-03-31
```

For regular updates, the services automatically fetch the latest data at intervals defined by the `DATA_FETCH_INTERVAL_HOURS` environment variable (default: 12 hours).

## Recent Updates

### Campaign Name Mapping Enhancement
- Added comprehensive campaign name mapping functionality allowing users to:
  - Create user-friendly names for campaigns across different platforms
  - Categorize campaigns with consistent labels
  - Track campaign types for better reporting
  - View source network information (Search, Display, Shopping, etc.)

### Network Information Tracking
- Added network identification and filtering across all ad platforms
- Enhanced reporting with network context for better analysis
- Improved campaign mapping with network-specific grouping
- Updated dashboard views to display network information alongside campaigns

## Deployment

The project is configured for deployment on Railway:

1. Push your code to GitHub
2. Create a new project on Railway
3. Connect to your GitHub repository
4. Set up the environment variables in Railway dashboard
5. Deploy!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
