# Google Ads Connector for SCARE Unified Dashboard

This module connects to the Google Ads API to fetch campaign performance metrics and stores them in the SCARE Unified Dashboard database.

## Features

- Fetches campaign performance data from Google Ads API
- Stores metrics like impressions, clicks, cost, and conversions
- Supports scheduled data fetching and backfilling
- Designed to work with Railway deployment

## Scripts

### main.py

The main connector script that includes:
- API authentication
- Data fetching from Google Ads
- Database storage with dimension tables
- Scheduled execution capabilities

### fetch_only.py

A standalone script to fetch data from Google Ads API and save it to CSV/JSON without requiring database access. Useful for:
- Testing API connectivity
- Generating data files for later import
- Analyzing Google Ads data without database dependencies

Usage:
```
python fetch_only.py
```

This will save the data to `google_ads_data.csv` and `google_ads_data.json`.

### import_from_json.py

A script to import previously fetched Google Ads data from a JSON file into the database. Useful for:
- Importing data when direct database access was previously unavailable
- Restoring data from backups
- Manual data imports

Usage:
```
python import_from_json.py [path_to_json_file]
```

If no path is provided, it will default to `google_ads_data.json`.

### test_fetch.py

A simple script to test the Google Ads API connection and data fetching functionality.

### debug.py

A debug script for API connection troubleshooting.

## Two-Step ETL Process

For Railway deployment, we recommend a two-step ETL process to handle potential database connectivity issues:

1. **Step 1**: Run `fetch_only.py` to get Google Ads data and save to JSON
2. **Step 2**: Run `import_from_json.py` to import the data into the database

This approach provides more resilience in case of:
- Intermittent database connectivity
- Database credential changes
- API timeouts during data fetching

## Configuration

All configuration is managed through environment variables:

```
# Database
DATABASE_URL=postgresql://scare_user:scare_password@localhost:5432/scare_metrics

# Google Ads API
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_client_id
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=your_customer_id
```

For Railway deployment, make sure to update the DATABASE_URL to match the Railway PostgreSQL service connection string.

## Error Handling

The scripts include comprehensive error handling:
- API connection errors are logged with details
- Database errors are caught with data saved to JSON for later retry
- Dimension table lookups handle missing values gracefully

## Logging

All scripts use Python's built-in logging module to provide detailed logs of their operation.
