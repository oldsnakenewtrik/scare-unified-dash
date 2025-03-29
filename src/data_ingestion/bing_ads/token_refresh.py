"""
Bing Ads OAuth token refresh module
Handles automatic refresh of Bing Ads OAuth tokens for continuous operation in Railway
"""
import os
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bing_ads_token_refresh')

# File path for storing the current token
TOKEN_FILE_PATH = os.path.join(os.path.dirname(__file__), 'credentials', 'access_token.json')
CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), 'credentials')

def ensure_credentials_dir():
    """Ensure the credentials directory exists"""
    if not os.path.exists(CREDENTIALS_DIR):
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)

def refresh_token():
    """
    Automatically refresh the Bing Ads OAuth token
    
    Returns:
        bool: True if token was refreshed successfully, False otherwise
    """
    ensure_credentials_dir()
    try:
        # Get existing credentials from environment
        client_id = os.environ.get("BING_ADS_CLIENT_ID")
        client_secret = os.environ.get("BING_ADS_CLIENT_SECRET")
        refresh_token = os.environ.get("BING_ADS_REFRESH_TOKEN")
        
        if not all([client_id, client_secret, refresh_token]):
            logger.error("Missing Bing Ads credentials for token refresh")
            return False
            
        # Use Microsoft's OAuth token endpoint
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://ads.microsoft.com/msads.manage offline_access"
        }
        
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            # Store the new access token and refresh token if provided
            token_info = {
                "access_token": token_data["access_token"],
                "expires_at": time.time() + token_data["expires_in"],
                "last_refreshed": datetime.now().isoformat()
            }
            
            # Microsoft sometimes provides a new refresh token
            if "refresh_token" in token_data:
                token_info["refresh_token"] = token_data["refresh_token"]
                # Consider updating the environment variable or securely storing it
                logger.info("New refresh token received from Microsoft")
            
            with open(TOKEN_FILE_PATH, "w") as f:
                json.dump(token_info, f)
                
            logger.info("Successfully refreshed Bing Ads token")
            return True
        else:
            logger.error(f"Failed to refresh Bing Ads token: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error refreshing Bing Ads token: {e}")
        return False

def get_access_token():
    """
    Get the current access token, refreshing if necessary
    
    Returns:
        str: The current access token or None if retrieval/refresh failed
    """
    ensure_credentials_dir()
    try:
        # Check if token file exists
        if os.path.exists(TOKEN_FILE_PATH):
            with open(TOKEN_FILE_PATH, "r") as f:
                token_data = json.load(f)
            
            # If token is close to expiring, refresh it (5 min buffer)
            if token_data.get("expires_at", 0) < time.time() + 300:
                if refresh_token():
                    # Re-read the refreshed token
                    with open(TOKEN_FILE_PATH, "r") as f:
                        token_data = json.load(f)
                else:
                    return None
            
            return token_data.get("access_token")
        else:
            # No token file, try refreshing
            if refresh_token():
                with open(TOKEN_FILE_PATH, "r") as f:
                    token_data = json.load(f)
                return token_data.get("access_token")
            return None
    except Exception as e:
        logger.error(f"Error getting Bing Ads access token: {e}")
        return None

def get_refresh_token():
    """
    Get the latest refresh token (might be newer than environment variable)
    
    Returns:
        str: The current refresh token or None if not available
    """
    ensure_credentials_dir()
    try:
        if os.path.exists(TOKEN_FILE_PATH):
            with open(TOKEN_FILE_PATH, "r") as f:
                token_data = json.load(f)
            
            if "refresh_token" in token_data:
                return token_data["refresh_token"]
        
        # Fall back to environment variable
        return os.environ.get("BING_ADS_REFRESH_TOKEN")
    except Exception as e:
        logger.error(f"Error getting Bing Ads refresh token: {e}")
        return os.environ.get("BING_ADS_REFRESH_TOKEN")

def schedule_token_refresh():
    """Schedule a regular token refresh before expiration"""
    # Refresh token now
    refresh_token()
    
    # Schedule next refresh in 50 minutes (tokens usually valid for 60 minutes)
    # Note: In a real implementation, you'd use a scheduler like APScheduler or similar
    logger.info("Token refresh will be handled by the scheduler")

if __name__ == "__main__":
    # This can be run independently to test token refresh
    if refresh_token():
        logger.info("Token refresh test successful")
    else:
        logger.error("Token refresh test failed")
