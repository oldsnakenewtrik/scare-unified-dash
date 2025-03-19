# API Credentials Setup Guide

This guide explains how to obtain API credentials for each platform integrated with the SCARE Unified Dashboard.

## Table of Contents
- [Google Ads](#google-ads)
- [Bing Ads](#bing-ads)
- [RedTrack](#redtrack)
- [Matomo](#matomo)
- [Salesforce](#salesforce)

## Google Ads

### Prerequisites
- A Google Ads account with administrative access
- A Google Cloud Platform account

### Steps
1. **Create a Google Cloud Platform Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Ads API

2. **Create OAuth Credentials**
   - In your GCP project, go to "APIs & Services" > "Credentials"
   - Create an OAuth 2.0 Client ID
   - Configure the OAuth consent screen
   - Set authorized redirect URIs (you can use http://localhost:8080/oauth2callback for testing)

3. **Get a Developer Token**
   - Log in to your Google Ads account
   - Go to Tools & Settings > Setup > API Center
   - Request a developer token
   - For testing, you can use a test account developer token
   - For production, submit a request to Google for approval

4. **Get a Refresh Token**
   - Use the Google OAuth 2.0 Playground (https://developers.google.com/oauthplayground/)
   - In the gear icon (settings), check "Use your own OAuth credentials" and enter your Client ID and Client Secret
   - Under "Step 1", select "Google Ads API v16" or search for "adwords" and select "https://www.googleapis.com/auth/adwords"
   - Click "Authorize APIs" and follow the login process
   - In "Step 2", click "Exchange authorization code for tokens"
   - Copy the Refresh token value

5. **Find Your Customer ID**
   - Log into your Google Ads account
   - Look at the account ID in the top right corner, which is in the format XXX-XXX-XXXX
   - Remove the dashes when using it as the CUSTOMER_ID in the API

6. **Update Environment Variables**
   - Add these values to your `.env` file:
     ```
     GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
     GOOGLE_ADS_CLIENT_ID=your_client_id
     GOOGLE_ADS_CLIENT_SECRET=your_client_secret
     GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
     GOOGLE_ADS_CUSTOMER_ID=your_customer_id (without dashes)
     ```

### Current Google Ads Configuration Status
- Client ID: Configured
- Client Secret: Configured 
- Refresh Token: Configured
- Developer Token: Needs to be obtained from Google Ads account
- Customer ID: Needs to be obtained from Google Ads account

### Testing Connection
To test your Google Ads API connection:
```
cd src/data_ingestion/google_ads
python main.py --check-health
```

## Bing Ads

### Prerequisites
- A Bing Ads account with administrative access
- A Microsoft account

### Steps
1. **Register an Application**
   - Go to the [Microsoft Application Registration Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
   - Register a new application
   - Set the redirect URI (e.g., http://localhost:8080/callback)

2. **Get Developer Token**
   - Log in to your Bing Ads account
   - Go to Account Settings > Developer Token
   - Request a developer token

3. **Get OAuth Credentials**
   - From your registered application, get the Application ID (Client ID)
   - Generate a new Client Secret

4. **Get a Refresh Token**
   - Use a script or tool to complete the OAuth flow
   - Store the refresh token securely

5. **Update Environment Variables**
   - Add these values to your `.env` file:
     ```
     BING_ADS_DEVELOPER_TOKEN=your_developer_token
     BING_ADS_CLIENT_ID=your_app_id
     BING_ADS_CLIENT_SECRET=your_client_secret
     BING_ADS_REFRESH_TOKEN=your_refresh_token
     BING_ADS_ACCOUNT_ID=your_account_id
     ```

## RedTrack

### Prerequisites
- A RedTrack account with API access

### Steps
1. **Get API Key**
   - Log in to your RedTrack account
   - Go to Settings > API Access
   - Generate a new API key

2. **Update Environment Variables**
   - Add these values to your `.env` file:
     ```
     REDTRACK_API_KEY=your_api_key
     REDTRACK_BASE_URL=https://api.redtrack.io
     ```

## Matomo

### Prerequisites
- A Matomo (formerly Piwik) analytics installation
- Administrative access to your Matomo instance

### Steps
1. **Get API Access Token**
   - Log in to your Matomo admin panel
   - Go to Settings > Personal > Security
   - Create a new Auth Token
   - Note your Site ID (visible in the Matomo interface)

2. **Update Environment Variables**
   - Add these values to your `.env` file:
     ```
     MATOMO_API_URL=https://your-matomo-instance.com/index.php
     MATOMO_SITE_ID=your_site_id
     MATOMO_AUTH_TOKEN=your_auth_token
     ```

## Salesforce

### Prerequisites
- A Salesforce account
- An email account that receives Salesforce reports

### Steps
1. **Email Report Configuration**
   - Set up Salesforce to send scheduled reports to an email address
   - Configure your email settings

2. **Update Environment Variables**
   - Add these values to your `.env` file:
     ```
     IMAP_SERVER=your_imap_server (e.g., imap.gmail.com)
     IMAP_PORT=your_imap_port (typically 993 for SSL)
     IMAP_USER=your_email@example.com
     IMAP_PASSWORD=your_email_password
     CHECK_EMAIL_CRON_SCHEDULE="0 */6 * * *"  # Check every 6 hours
     ```

## Creating Your .env File

1. Copy the `.env.template` file to a new file named `.env`
2. Replace all placeholder values with your actual API credentials
3. Ensure the `.env` file is excluded from version control (it should be in .gitignore)

## Testing Your Connections

After setting up all credentials, you can test each connection:

```bash
# Start the services
docker compose up -d

# Check logs for each connector
docker compose logs -f redtrack
docker compose logs -f google_ads
docker compose logs -f bing_ads
docker compose logs -f matomo
docker compose logs -f salesforce
```

Each service should connect successfully and begin fetching data.
