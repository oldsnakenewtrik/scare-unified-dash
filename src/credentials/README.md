# Credentials Directory

This directory is designated for storing API credentials and sensitive configuration files that should not be committed to version control.

## Purpose

The credentials directory provides a centralized location for all authentication files and API keys needed by the various data connectors in the SCARE Unified Dashboard application.

## Usage

### Storing Credentials

1. Create credential files in this directory following the patterns below
2. Reference these files in your environment variables or application code
3. Never commit actual credential files to version control (they are ignored via .gitignore)

### Recommended File Structure

```
credentials/
├── google_ads/
│   ├── google-ads.yaml        # Google Ads API configuration
│   └── client_secrets.json    # OAuth client credentials
├── bing_ads/
│   └── auth.json              # Bing Ads authentication details
├── redtrack/
│   └── api_keys.json          # RedTrack API keys
└── salesforce/
    └── auth_config.json       # Salesforce authentication details
```

## Setting Up

For local development:
1. Create the appropriate subdirectories and credential files as shown above
2. Add your actual API keys, tokens, and other credentials to these files
3. Update your local `.env` file to point to these credential files

For deployment:
1. Securely transfer your credential files to the production environment
2. Configure your environment variables to use these credentials
3. Consider using Railway's secret management for production deployments

## Security Best Practices

- Never hardcode credentials directly in application code
- Rotate API keys and refresh tokens regularly
- Use the least privileged access required for each integration
- Protect your `.env` file and this directory from unauthorized access
- Consider using environment-specific credential files (dev, staging, prod)
