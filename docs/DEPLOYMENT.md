# Google Ads Integration Deployment Guide

This guide explains how to deploy the updated SCARE Unified Dashboard with Google Ads integration.

## Changes Made

1. **Added database view creation**:
   - Created `sm_unified_ads_metrics` view to combine data from all ad platforms
   - Created `sm_campaign_performance` view to aggregate metrics for reporting
   - Ensured views include `pretty_network` and `pretty_source` fields from mappings

2. **Added post-deployment scripts**:
   - Created `post_deploy.py` to ensure views are created on application startup
   - Updated `docker_entrypoint.sh` to run post-deployment tasks

3. **Improved database connection resilience**:
   - Added retries and better error handling for database operations
   - Implemented consistent engine creation logic across components

## Deployment Steps

1. **Push changes to your Railway repository**:
   ```bash
   git add .
   git commit -m "Added database views for Google Ads integration"
   git push
   ```

2. **Verify in Railway**:
   - After deployment completes, check the logs for:
     - "Creating or updating database views" message
     - "Found X rows in Google Ads fact table" message
     - "sm_unified_ads_metrics view created or updated" message

3. **Verify data in the dashboard**:
   - Navigate to your dashboard
   - Check that Google Ads campaign metrics are visible
   - Verify that campaign mappings are working correctly

## Manual Verification (if needed)

If you need to manually check if the views were created:

1. Connect to your Railway database:
   ```bash
   psql $RAILWAY_DATABASE_URL
   ```

2. Check if views exist:
   ```sql
   \dv
   SELECT COUNT(*) FROM sm_unified_ads_metrics WHERE platform = 'google_ads';
   SELECT COUNT(*) FROM sm_campaign_performance WHERE platform = 'google_ads';
   ```

## Troubleshooting

If Google Ads data isn't showing in the dashboard:

1. **Check view creation**:
   ```bash
   railway run python post_deploy.py
   ```

2. **Run ETL process manually**:
   ```bash
   railway run python src/data_ingestion/google_ads/run_etl.py --days 7
   ```

3. **Check for error logs**:
   ```bash
   railway logs
   ```

## Future Enhancements

- Consider implementing scheduled data refreshes using Railway Cron
- Add data validation checks to ensure data quality
- Implement monitoring for ETL process success/failure
