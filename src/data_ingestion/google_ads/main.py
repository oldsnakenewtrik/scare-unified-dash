import os
import sys
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sqlalchemy as sa
from token_refresh import get_access_token, refresh_token
import schedule
import time
import json
import yaml
from pathlib import Path
from sqlalchemy import text
import requests
import traceback # Already used later, ensure it's here
from google.auth.exceptions import RefreshError # For catching token errors

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('google_ads_connector')

# Load environment variables
load_dotenv()

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
except ImportError:
    logger.error("Failed to import Google Ads API libraries. Make sure they are installed.")
    sys.exit(1)

# Google Ads API credentials
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN')
GOOGLE_ADS_CLIENT_ID = os.getenv('GOOGLE_ADS_CLIENT_ID')
GOOGLE_ADS_CLIENT_SECRET = os.getenv('GOOGLE_ADS_CLIENT_SECRET')
GOOGLE_ADS_REFRESH_TOKEN = os.getenv('GOOGLE_ADS_REFRESH_TOKEN')
GOOGLE_ADS_CUSTOMER_ID = os.getenv('GOOGLE_ADS_CUSTOMER_ID')

# Create database engine
def get_db_engine():
    """
    Create and return a SQLAlchemy database engine using Railway PostgreSQL variables
    """
    # Check for Railway postgres variables first
    postgres_host = os.getenv('PGHOST', 'postgres.railway.internal')
    postgres_port = os.getenv('PGPORT', '5432')
    postgres_user = os.getenv('PGUSER', 'postgres')
    postgres_password = os.getenv('PGPASSWORD')
    postgres_db = os.getenv('PGDATABASE', 'railway')
    
    # Fallback to generic DATABASE_URL if specific variables aren't available
    database_url = os.getenv('DATABASE_URL')
    railway_database_url = os.getenv('RAILWAY_DATABASE_URL')
    
    # Log connection attempt for debugging
    logger.info("Attempting to create database engine...")
    
    if postgres_password and postgres_host:
        # Construct connection string
        connection_string = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
        logger.info(f"Creating database engine with Railway PostgreSQL variables (host: {postgres_host})")
        return sa.create_engine(connection_string)
    elif railway_database_url:
        logger.info("Creating database engine with RAILWAY_DATABASE_URL environment variable")
        return sa.create_engine(railway_database_url)
    elif database_url:
        logger.info("Creating database engine with DATABASE_URL environment variable")
        return sa.create_engine(database_url)
    else:
        logger.error("No database connection information found in environment variables")
        # Print available environment variables for debugging
        logger.info("Available environment variables:")
        for key in os.environ:
            if "DATABASE" in key or "PG" in key or "SQL" in key:
                logger.info(f"  - {key}: {'*' * min(len(os.environ[key]), 5)}")
        return None

# Create engine
engine = get_db_engine()

def update_system_status(key, value):
    """Updates a key-value pair in the system_status table."""
    if not engine:
        logger.error("Cannot update system status, database engine not available.")
        return
    
    try:
        with engine.connect() as conn:
            # Use INSERT ... ON CONFLICT DO UPDATE (Upsert)
            stmt = text("""
                INSERT INTO public.system_status (status_key, status_value, updated_at)
                VALUES (:key, :value, NOW())
                ON CONFLICT (status_key) DO UPDATE
                SET status_value = EXCLUDED.status_value,
                    updated_at = NOW();
            """)
            conn.execute(stmt, {'key': key, 'value': value})
            logger.info(f"System status updated: {key} = {value}")
    except Exception as e:
        logger.error(f"Failed to update system status for key '{key}': {str(e)}")
        # Log traceback for detailed debugging
        logger.error(traceback.format_exc())

def get_google_ads_client():
    """Get a Google Ads API client."""
    try:
        # Try to load the client from YAML
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        # Determine the customer ID
        yaml_paths = [
            # Local development path
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            # Railway paths
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            # Railway repository root path
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        # Try different API versions
        api_versions = ["v11", "v14", "v16", "v18", "v21"]
        
        for api_version in api_versions:
            logger.info(f"Trying to create Google Ads client with API version {api_version}")
            
            for path in yaml_paths:
                if os.path.exists(path):
                    try:
                        # Explicitly import the version-specific client
                        if api_version == "v11":
                            from google.ads.googleads.v11 import GoogleAdsClient
                        elif api_version == "v14":
                            from google.ads.googleads.v14 import GoogleAdsClient
                        elif api_version == "v16":
                            from google.ads.googleads.v16 import GoogleAdsClient
                        elif api_version == "v18":
                            from google.ads.googleads.v18 import GoogleAdsClient
                        elif api_version == "v21":
                            from google.ads.googleads.v21 import GoogleAdsClient
                        else:
                            # Default to the main client
                            from google.ads.googleads.client import GoogleAdsClient
                        
                        logger.info(f"Loading Google Ads client from YAML: {path}")
                        client = GoogleAdsClient.load_from_storage(path)
                        logger.info(f"Successfully created Google Ads client with API version {api_version}")
                        return client
                    except Exception as e:
                        logger.warning(f"Failed to create Google Ads client with API version {api_version} from {path}: {str(e)}")
                        continue
        
        # If we couldn't create a client from YAML, try using environment variables
        logger.info("Trying to create Google Ads client from environment variables")
        
        # Get credentials from environment variables
        developer_token = GOOGLE_ADS_DEVELOPER_TOKEN
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        
        if not all([developer_token, client_id, client_secret, refresh_token]):
            logger.error("Missing required environment variables for Google Ads API")
            return None
        
        # Try different API versions with environment variables
        for api_version in api_versions:
            try:
                # Explicitly import the version-specific client
                if api_version == "v11":
                    from google.ads.googleads.v11 import GoogleAdsClient
                elif api_version == "v14":
                    from google.ads.googleads.v14 import GoogleAdsClient
                elif api_version == "v16":
                    from google.ads.googleads.v16 import GoogleAdsClient
                elif api_version == "v18":
                    from google.ads.googleads.v18 import GoogleAdsClient
                elif api_version == "v21":
                    from google.ads.googleads.v21 import GoogleAdsClient
                else:
                    # Default to the main client
                    from google.ads.googleads.client import GoogleAdsClient
                
                logger.info(f"Creating Google Ads client from environment variables with API version {api_version}")
                client = GoogleAdsClient.load_from_dict({
                    "developer_token": developer_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "use_proto_plus": True
                })
                logger.info(f"Successfully created Google Ads client with API version {api_version}")
                return client
            except Exception as e:
                logger.warning(f"Failed to create Google Ads client with API version {api_version} from environment variables: {str(e)}")
                continue
        
        logger.error("Failed to create Google Ads client with any API version")
        # Update status if client creation failed potentially due to auth
        update_system_status('google_ads_auth_status', 'error: client creation failed')
        return None
    except RefreshError as re:
        # Specific error for refresh token issues
        logger.error(f"Google Ads Refresh Token Error: {str(re)}")
        logger.error(traceback.format_exc())
        update_system_status('google_ads_auth_status', 'error: refresh token invalid')
        return None
    except Exception as e:
        logger.error(f"Error creating Google Ads client: {str(e)}")
        logger.error(traceback.format_exc())
        # Update status for generic errors during client creation
        update_system_status('google_ads_auth_status', f'error: {str(e)}')
        return None

def get_campaign_dimension_id(campaign_name, source_campaign_id=None):
    """
    Get or create a campaign dimension ID.
    
    Args:
        campaign_name (str): Name of the campaign
        source_campaign_id (str, optional): Original campaign ID from the source system
        
    Returns:
        int: Campaign dimension ID
    """
    with engine.connect() as conn:
        # Check if campaign exists
        query = sa.text("""
            SELECT campaign_id FROM scare_metrics.dim_campaign 
            WHERE campaign_name = :name OR source_campaign_id = :source_id
        """)
        
        result = conn.execute(query, {"name": campaign_name, "source_id": source_campaign_id}).fetchone()
        
        if result:
            return result[0]
        
        # Insert new campaign
        query = sa.text("""
            INSERT INTO scare_metrics.dim_campaign 
            (campaign_name, source_campaign_id, source_system, created_at) 
            VALUES (:name, :source_id, 'Google Ads', :created_at)
            RETURNING campaign_id
        """)
        
        result = conn.execute(query, {
            "name": campaign_name, 
            "source_id": source_campaign_id, 
            "created_at": datetime.now()
        }).fetchone()
        
        return result[0]

def get_date_dimension_id(date_str):
    """
    Get or create a date dimension ID.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        int: Date dimension ID
    """
    with engine.connect() as conn:
        try:
            # Parse date string to datetime object
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Extract date components
            year = date_obj.year
            month = date_obj.month
            day = date_obj.day
            
            # Check if date exists
            query = sa.text("""
                SELECT date_id FROM scare_metrics.dim_date 
                WHERE year = :year AND month = :month AND day = :day
            """)
            
            result = conn.execute(query, {"year": year, "month": month, "day": day}).fetchone()
            
            if result:
                return result[0]
            
            # Insert new date
            query = sa.text("""
                INSERT INTO scare_metrics.dim_date 
                (year, month, day, full_date) 
                VALUES (:year, :month, :day, :full_date)
                RETURNING date_id
            """)
            
            result = conn.execute(query, {
                "year": year, 
                "month": month, 
                "day": day, 
                "full_date": date_obj
            }).fetchone()
            
            return result[0]
        except Exception as e:
            logger.error(f"Error getting date dimension ID: {str(e)}")
            # Return a default ID if something goes wrong
            return 1  # You may want to adjust this to a different strategy

def check_google_ads_health():
    """Test if we can connect to the Google Ads API and fetch basic data."""
    logger.info("Testing Google Ads API connection...")
    
    try:
        # Try to create a client
        client = get_google_ads_client()
        if not client:
            logger.error("❌ Failed to create Google Ads client")
            return False
        
        logger.info("✅ Successfully created Google Ads client")
        
        # Test basic API query
        try:
            # Simple query to fetch account information
            ga_service = client.get_service("GoogleAdsService")
            query = """
                SELECT customer.id, customer.descriptive_name
                FROM customer
                LIMIT 1
            """
            
            # Use search instead of search_stream for compatibility
            response = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query)
            
            # Process the response
            result_count = 0
            for row in response:
                result_count += 1
                logger.info(f"✅ Successfully connected to Google Ads account: {row.customer.descriptive_name} (ID: {row.customer.id})")
            
            if result_count > 0:
                return True
            
            logger.info("✅ Connected to API but no account information found.")
            return True
            
        except GoogleAdsException as ex:
            logger.error(f"❌ Google Ads API error: {ex.error.code().name}")
            for error in ex.failure.errors:
                logger.error(f"  - Error message: {error.message}")
                if error.location:
                    for field_path_element in error.location.field_path_elements:
                        logger.error(f"    - On field: {field_path_element.field_name}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to connect to Google Ads API: {str(e)}")
        return False

def fetch_google_ads_data_rest_fallback(start_date, end_date):
    """
    Fallback method to fetch data from Google Ads API using REST API instead of gRPC.
    This is used when the gRPC method fails with 'GRPC target method can't be resolved'.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Attempting to fetch Google Ads data via REST API from {start_date} to {end_date}...")
    
    try:
        # Get credentials from environment variables or YAML
        developer_token = GOOGLE_ADS_DEVELOPER_TOKEN
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        customer_id = GOOGLE_ADS_CUSTOMER_ID
        
        # Try to load from YAML if available
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"Loading credentials from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    developer_token = config.get('developer_token', developer_token)
                    client_id = config.get('client_id', client_id)
                    client_secret = config.get('client_secret', client_secret)
                    refresh_token = config.get('refresh_token', refresh_token)
                    customer_id = config.get('customer_id', customer_id) or config.get('login_customer_id', customer_id)
                    break
        
        # Ensure customer_id is a string
        customer_id = str(customer_id)
        logger.info(f"Using customer ID: {customer_id}")
        
        # Get access token
        token_url = "https://accounts.google.com/o/oauth2/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        logger.info("Requesting OAuth2 access token...")
        token_response = None # Initialize for error handling scope
        try:
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            access_token = token_response.json().get("access_token")
            if not access_token:
                logger.error("Access token not found in response.")
                update_system_status('google_ads_auth_status', 'error: access token missing')
                return []
            logger.info("Successfully obtained access token")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Failed to get access token (RequestException): {str(req_err)}")
            # Check if it's likely a refresh token error (e.g., 400 Bad Request with 'invalid_grant')
            if token_response and token_response.status_code == 400 and 'invalid_grant' in token_response.text.lower():
                logger.error("Refresh token appears to be invalid (invalid_grant).")
                update_system_status('google_ads_auth_status', 'error: refresh token invalid')
            else:
                update_system_status('google_ads_auth_status', f'error: token request failed ({str(req_err)})')
            return []
        except Exception as e: # Catch other potential errors like JSONDecodeError
            logger.error(f"Failed to get access token (Other Error): {str(e)}")
            logger.error(traceback.format_exc())
            update_system_status('google_ads_auth_status', f'error: token request failed ({str(e)})')
            return []
        
        # Try different API versions and endpoint formats
        api_versions = ["v11", "v14", "v16", "v18", "v21"]
        endpoint_formats = [
            # Standard REST API endpoint format
            "https://googleads.googleapis.com/{version}/customers/{customer_id}:search",
            # Alternative format with googleAds prefix
            "https://googleads.googleapis.com/{version}/customers/{customer_id}/googleAds:search",
            # Format with Google Ads service
            "https://googleads.googleapis.com/{version}/customers/{customer_id}/googleAdsService:search",
            # Format with services path
            "https://googleads.googleapis.com/{version}/services/googleAdsService:search",
            # Format with services and customer ID
            "https://googleads.googleapis.com/{version}/services/googleAdsService/{customer_id}:search"
        ]
        
        for api_version in api_versions:
            logger.info(f"Trying Google Ads REST API version {api_version}")
            
            # Construct the Google Ads API query
            query = f"""
                SELECT
                  campaign.id,
                  campaign.name,
                  metrics.impressions,
                  metrics.clicks,
                  metrics.cost_micros,
                  segments.date
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                LIMIT 1000
            """
            
            for endpoint_format in endpoint_formats:
                # Make the REST API request
                url = endpoint_format.format(version=api_version, customer_id=customer_id)
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": developer_token,
                    "Content-Type": "application/json"
                }
                
                data = {
                    "query": query
                }
                
                logger.info(f"Making REST API request to {url}")
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code != 200:
                    logger.warning(f"Google Ads API REST request failed with version {api_version} and endpoint {url}: {response.status_code}")
                    logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars to avoid huge logs
                    continue
                
                # Process the response
                try:
                    response_json = response.json()
                    results = []
                    
                    # Check if we have results
                    if "results" in response_json:
                        for result in response_json["results"]:
                            campaign = result.get("campaign", {})
                            metrics = result.get("metrics", {})
                            segments = result.get("segments", {})
                            
                            row_data = {
                                "campaign_id": campaign.get("id", ""),
                                "campaign_name": campaign.get("name", ""),
                                "impressions": metrics.get("impressions", 0),
                                "clicks": metrics.get("clicks", 0),
                                "cost_micros": metrics.get("costMicros", 0),
                                "date": segments.get("date", "")
                            }
                            
                            results.append(row_data)
                    
                    logger.info(f"Successfully fetched {len(results)} rows of Google Ads data via REST API v{api_version}")
                    return results
                except Exception as e:
                    logger.error(f"Error processing REST API response for version {api_version}: {str(e)}")
                    continue
        
        logger.error("All REST API versions and endpoints failed")
        return []
        
    except Exception as e:
        logger.error(f"Error fetching Google Ads data via REST API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def fetch_google_ads_data_discovery_fallback(start_date, end_date):
    """
    Fallback method that uses the Google Ads API discovery document to determine the
    correct API version and endpoint.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Attempting to fetch Google Ads data via discovery document from {start_date} to {end_date}...")
    
    try:
        # Get credentials from environment variables or YAML
        developer_token = GOOGLE_ADS_DEVELOPER_TOKEN
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        customer_id = GOOGLE_ADS_CUSTOMER_ID
        
        # Try to load from YAML if available
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"Loading credentials from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    developer_token = config.get('developer_token', developer_token)
                    client_id = config.get('client_id', client_id)
                    client_secret = config.get('client_secret', client_secret)
                    refresh_token = config.get('refresh_token', refresh_token)
                    customer_id = config.get('customer_id', customer_id) or config.get('login_customer_id', customer_id)
                    break
        
        # Ensure customer_id is a string
        customer_id = str(customer_id)
        logger.info(f"Using customer ID: {customer_id}")
        
        # Get access token
        token_url = "https://accounts.google.com/o/oauth2/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        logger.info("Requesting OAuth2 access token...")
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            logger.error(f"Failed to get access token: {token_response.text}")
            return []
        
        access_token = token_response.json().get("access_token")
        logger.info("Successfully obtained access token")
        
        # Fetch the discovery document to get the correct API version and endpoints
        discovery_urls = [
            "https://googleads.googleapis.com/$discovery/rest?version=v11",
            "https://googleads.googleapis.com/$discovery/rest?version=v14",
            "https://googleads.googleapis.com/$discovery/rest?version=v16",
            "https://googleads.googleapis.com/$discovery/rest?version=v18",
            "https://googleads.googleapis.com/$discovery/rest?version=v21"
        ]
        
        for discovery_url in discovery_urls:
            logger.info(f"Fetching discovery document from {discovery_url}")
            
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            discovery_response = requests.get(discovery_url, headers=headers)
            if discovery_response.status_code != 200:
                logger.warning(f"Failed to fetch discovery document: {discovery_response.status_code}")
                continue
            
            try:
                discovery_doc = discovery_response.json()
                logger.info(f"Successfully fetched discovery document for {discovery_url}")
                
                # Extract API version from the discovery document
                api_version = discovery_doc.get("version")
                logger.info(f"Discovery document API version: {api_version}")
                
                # Find the search method in the discovery document
                search_method = None
                resources = discovery_doc.get("resources", {})
                for resource_name, resource in resources.items():
                    methods = resource.get("methods", {})
                    if "search" in methods:
                        search_method = methods["search"]
                        logger.info(f"Found search method in resource: {resource_name}")
                        break
                    
                    # Check nested resources
                    nested_resources = resource.get("resources", {})
                    for nested_name, nested_resource in nested_resources.items():
                        nested_methods = nested_resource.get("methods", {})
                        if "search" in nested_methods:
                            search_method = nested_methods["search"]
                            logger.info(f"Found search method in nested resource: {resource_name}.{nested_name}")
                            break
                    
                    if search_method:
                        break
                
                if not search_method:
                    logger.warning("Could not find search method in discovery document")
                    continue
                
                # Get the HTTP method and path
                http_method = search_method.get("httpMethod", "POST")
                path = search_method.get("path", "")
                
                logger.info(f"Search method HTTP method: {http_method}")
                logger.info(f"Search method path: {path}")
                
                # Construct the URL
                base_url = discovery_doc.get("rootUrl", "https://googleads.googleapis.com/")
                service_path = discovery_doc.get("servicePath", "")
                full_url = base_url + service_path + path.replace("{+name}", f"customers/{customer_id}")
                
                logger.info(f"Constructed URL: {full_url}")
                
                # Construct the Google Ads API query
                query = f"""
                    SELECT
                      campaign.id,
                      campaign.name,
                      metrics.impressions,
                      metrics.clicks,
                      metrics.cost_micros,
                      segments.date
                    FROM campaign
                    WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                    LIMIT 1000
                """
                
                # Make the API request
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": developer_token,
                    "Content-Type": "application/json"
                }
                
                data = {
                    "query": query
                }
                
                logger.info(f"Making API request to {full_url}")
                response = requests.post(full_url, headers=headers, json=data)
                
                if response.status_code != 200:
                    logger.warning(f"API request failed: {response.status_code}")
                    logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars to avoid huge logs
                    continue
                
                # Process the response
                try:
                    response_json = response.json()
                    results = []
                    
                    # Check if we have results
                    if "results" in response_json:
                        for result in response_json["results"]:
                            campaign = result.get("campaign", {})
                            metrics = result.get("metrics", {})
                            segments = result.get("segments", {})
                            
                            row_data = {
                                "campaign_id": campaign.get("id", ""),
                                "campaign_name": campaign.get("name", ""),
                                "impressions": metrics.get("impressions", 0),
                                "clicks": metrics.get("clicks", 0),
                                "cost_micros": metrics.get("costMicros", 0),
                                "date": segments.get("date", "")
                            }
                            
                            results.append(row_data)
                    
                    logger.info(f"Successfully fetched {len(results)} rows of Google Ads data via discovery document")
                    return results
                except Exception as e:
                    logger.error(f"Error processing response: {str(e)}")
                    continue
                
            except Exception as e:
                logger.error(f"Error parsing discovery document: {str(e)}")
                continue
        
        logger.error("All discovery document attempts failed")
        return []
        
    except Exception as e:
        logger.error(f"Error in discovery document fallback: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def fetch_google_ads_data_direct_fallback(start_date, end_date):
    """
    Last resort fallback method to fetch data from Google Ads API using direct HTTP requests
    with the google-auth library. This is used when both gRPC and REST API methods fail.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Attempting to fetch Google Ads data via direct HTTP from {start_date} to {end_date}...")
    
    try:
        # Import required libraries
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as AuthRequest
            import json
        except ImportError:
            logger.error("Required libraries not installed. Please install google-auth and google-auth-oauthlib.")
            return []
        
        # Get credentials from environment variables or YAML
        developer_token = GOOGLE_ADS_DEVELOPER_TOKEN
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        customer_id = GOOGLE_ADS_CUSTOMER_ID
        
        # Try to load from YAML if available
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"Loading credentials from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    developer_token = config.get('developer_token', developer_token)
                    client_id = config.get('client_id', client_id)
                    client_secret = config.get('client_secret', client_secret)
                    refresh_token = config.get('refresh_token', refresh_token)
                    customer_id = config.get('customer_id', customer_id) or config.get('login_customer_id', customer_id)
                    break
        
        # Ensure customer_id is a string
        customer_id = str(customer_id)
        logger.info(f"Using customer ID: {customer_id}")
        
        # Create credentials
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://accounts.google.com/o/oauth2/token",
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Refresh the credentials
        request = AuthRequest()
        credentials.refresh(request)
        
        # Try different API versions and endpoint formats
        api_versions = ["v11", "v14", "v16", "v18", "v21"]
        endpoint_formats = [
            # Standard REST API endpoint format
            "https://googleads.googleapis.com/{version}/customers/{customer_id}:search",
            # Alternative format with googleAds prefix
            "https://googleads.googleapis.com/{version}/customers/{customer_id}/googleAds:search",
            # Format with Google Ads service
            "https://googleads.googleapis.com/{version}/customers/{customer_id}/googleAdsService:search",
            # Format with services path
            "https://googleads.googleapis.com/{version}/services/googleAdsService:search",
            # Format with services and customer ID
            "https://googleads.googleapis.com/{version}/services/googleAdsService/{customer_id}:search"
        ]
        
        for api_version in api_versions:
            logger.info(f"Trying Google Ads API direct HTTP version {api_version}")
            
            # Construct the Google Ads API query
            query = f"""
                SELECT
                  campaign.id,
                  campaign.name,
                  metrics.impressions,
                  metrics.clicks,
                  metrics.cost_micros,
                  segments.date
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                LIMIT 1000
            """
            
            for endpoint_format in endpoint_formats:
                # Make the direct HTTP request
                url = endpoint_format.format(version=api_version, customer_id=customer_id)
                
                headers = {
                    "Authorization": f"Bearer {credentials.token}",
                    "developer-token": developer_token,
                    "Content-Type": "application/json"
                }
                
                data = {
                    "query": query
                }
                
                logger.info(f"Making direct HTTP request to {url}")
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code != 200:
                    logger.warning(f"Google Ads API direct HTTP request failed with version {api_version} and endpoint {url}: {response.status_code}")
                    logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars to avoid huge logs
                    continue
                
                # Process the response
                try:
                    response_json = response.json()
                    results = []
                    
                    # Check if we have results
                    if "results" in response_json:
                        for result in response_json["results"]:
                            campaign = result.get("campaign", {})
                            metrics = result.get("metrics", {})
                            segments = result.get("segments", {})
                            
                            row_data = {
                                "campaign_id": campaign.get("id", ""),
                                "campaign_name": campaign.get("name", ""),
                                "impressions": metrics.get("impressions", 0),
                                "clicks": metrics.get("clicks", 0),
                                "cost_micros": metrics.get("costMicros", 0),
                                "date": segments.get("date", "")
                            }
                            
                            results.append(row_data)
                    
                    logger.info(f"Successfully fetched {len(results)} rows of Google Ads data via direct HTTP v{api_version}")
                    return results
                except Exception as e:
                    logger.error(f"Error processing direct HTTP response for version {api_version}: {str(e)}")
                    continue
        
        logger.error("All direct HTTP API versions and endpoints failed")
        return []
        
    except Exception as e:
        logger.error(f"Error fetching Google Ads data via direct HTTP: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def fetch_google_ads_data_v11_fallback(start_date, end_date):
    """
    Special fallback method specifically for Google Ads API v11.
    This method uses the exact endpoint format from v11 documentation.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Attempting to fetch Google Ads data via v11 specific endpoint from {start_date} to {end_date}...")
    
    try:
        # Get credentials from environment variables or YAML
        developer_token = GOOGLE_ADS_DEVELOPER_TOKEN
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        customer_id = GOOGLE_ADS_CUSTOMER_ID
        
        # Try to load from YAML if available
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"Loading credentials from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    developer_token = config.get('developer_token', developer_token)
                    client_id = config.get('client_id', client_id)
                    client_secret = config.get('client_secret', client_secret)
                    refresh_token = config.get('refresh_token', refresh_token)
                    customer_id = config.get('customer_id', customer_id) or config.get('login_customer_id', customer_id)
                    break
        
        # Ensure customer_id is a string
        customer_id = str(customer_id)
        logger.info(f"Using customer ID: {customer_id}")
        
        # Get access token
        token_url = "https://accounts.google.com/o/oauth2/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        logger.info("Requesting OAuth2 access token...")
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            logger.error(f"Failed to get access token: {token_response.text}")
            return []
        
        access_token = token_response.json().get("access_token")
        logger.info("Successfully obtained access token")
        
        # v11 specific endpoint formats
        endpoint_formats = [
            # v11 GoogleAdsService.Search endpoint
            "https://googleads.googleapis.com/v11/customers/{customer_id}/googleAds:search",
            # Alternative v11 format
            "https://googleads.googleapis.com/v11/customers/{customer_id}/googleAdsService:search",
            # Another alternative format
            "https://googleads.googleapis.com/v11/services/GoogleAdsService/Search"
        ]
        
        # Construct the Google Ads API query
        query = f"""
            SELECT
              campaign.id,
              campaign.name,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            LIMIT 1000
        """
        
        for endpoint_format in endpoint_formats:
            # Make the REST API request
            url = endpoint_format.format(customer_id=customer_id)
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "developer-token": developer_token,
                "Content-Type": "application/json"
            }
            
            # v11 specific request format
            data = {
                "query": query
            }
            
            logger.info(f"Making v11 specific API request to {url}")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                logger.warning(f"Google Ads API v11 request failed with endpoint {url}: {response.status_code}")
                logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars to avoid huge logs
                continue
            
            # Process the response
            try:
                response_json = response.json()
                results = []
                
                # Check if we have results
                if "results" in response_json:
                    for result in response_json["results"]:
                        campaign = result.get("campaign", {})
                        metrics = result.get("metrics", {})
                        segments = result.get("segments", {})
                        
                        row_data = {
                            "campaign_id": campaign.get("id", ""),
                            "campaign_name": campaign.get("name", ""),
                            "impressions": metrics.get("impressions", 0),
                            "clicks": metrics.get("clicks", 0),
                            "cost_micros": metrics.get("costMicros", 0),
                            "date": segments.get("date", "")
                        }
                        
                        results.append(row_data)
                
                logger.info(f"Successfully fetched {len(results)} rows of Google Ads data via v11 specific endpoint")
                return results
            except Exception as e:
                logger.error(f"Error processing v11 specific API response: {str(e)}")
                continue
        
        logger.error("All v11 specific endpoints failed")
        return []
        
    except Exception as e:
        logger.error(f"Error fetching Google Ads data via v11 specific endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def fetch_google_ads_data_v11_special_auth(start_date, end_date):
    """
    Special fallback method for Google Ads API v11 with a different authentication approach.
    This method uses a different way to authenticate with the Google Ads API.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Attempting to fetch Google Ads data via v11 with special auth from {start_date} to {end_date}...")
    
    try:
        # Get credentials from environment variables or YAML
        developer_token = GOOGLE_ADS_DEVELOPER_TOKEN
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        customer_id = GOOGLE_ADS_CUSTOMER_ID
        
        # Try to load from YAML if available
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"Loading credentials from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    developer_token = config.get('developer_token', developer_token)
                    client_id = config.get('client_id', client_id)
                    client_secret = config.get('client_secret', client_secret)
                    refresh_token = config.get('refresh_token', refresh_token)
                    customer_id = config.get('customer_id', customer_id) or config.get('login_customer_id', customer_id)
                    break
        
        # Ensure customer_id is a string
        customer_id = str(customer_id)
        logger.info(f"Using customer ID: {customer_id}")
        
        # Import required libraries
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as AuthRequest
            from google.auth.transport.requests import AuthorizedSession
        except ImportError:
            logger.error("Required libraries not installed. Please install google-auth and google-auth-oauthlib.")
            return []
        
        # Create OAuth2 credentials
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://accounts.google.com/o/oauth2/token",
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Refresh the credentials
        request = AuthRequest()
        credentials.refresh(request)
        
        # Create an authorized session
        authed_session = AuthorizedSession(credentials)
        
        # v11 specific endpoint formats
        endpoint_formats = [
            # v11 GoogleAdsService.Search endpoint
            "https://googleads.googleapis.com/v11/customers/{customer_id}/googleAds:search",
            # Alternative v11 format
            "https://googleads.googleapis.com/v11/customers/{customer_id}/googleAdsService:search",
            # Another alternative format
            "https://googleads.googleapis.com/v11/services/GoogleAdsService/Search"
        ]
        
        # Construct the Google Ads API query
        query = f"""
            SELECT
              campaign.id,
              campaign.name,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              segments.date
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            LIMIT 1000
        """
        
        for endpoint_format in endpoint_formats:
            # Make the REST API request
            url = endpoint_format.format(customer_id=customer_id)
            
            headers = {
                "developer-token": developer_token,
                "Content-Type": "application/json"
            }
            
            # v11 specific request format
            data = {
                "query": query
            }
            
            logger.info(f"Making v11 special auth API request to {url}")
            response = authed_session.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                logger.warning(f"Google Ads API v11 special auth request failed with endpoint {url}: {response.status_code}")
                logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars to avoid huge logs
                continue
            
            # Process the response
            try:
                response_json = response.json()
                results = []
                
                # Check if we have results
                if "results" in response_json:
                    for result in response_json["results"]:
                        campaign = result.get("campaign", {})
                        metrics = result.get("metrics", {})
                        segments = result.get("segments", {})
                        
                        row_data = {
                            "campaign_id": campaign.get("id", ""),
                            "campaign_name": campaign.get("name", ""),
                            "impressions": metrics.get("impressions", 0),
                            "clicks": metrics.get("clicks", 0),
                            "cost_micros": metrics.get("costMicros", 0),
                            "date": segments.get("date", "")
                        }
                        
                        results.append(row_data)
                
                logger.info(f"Successfully fetched {len(results)} rows of Google Ads data via v11 special auth")
                return results
            except Exception as e:
                logger.error(f"Error processing v11 special auth API response: {str(e)}")
                continue
        
        logger.error("All v11 special auth endpoints failed")
        return []
        
    except Exception as e:
        logger.error(f"Error fetching Google Ads data via v11 special auth: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def fetch_google_ads_data_report_fetcher_fallback(start_date, end_date):
    """
    Last resort fallback method that uses a different approach to fetch Google Ads data.
    This method mimics the approach used by Google's ads-api-report-fetcher.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Attempting to fetch Google Ads data via report fetcher approach from {start_date} to {end_date}...")
    
    try:
        # Get credentials from environment variables or YAML
        developer_token = GOOGLE_ADS_DEVELOPER_TOKEN
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        customer_id = GOOGLE_ADS_CUSTOMER_ID
        
        # Try to load from YAML if available
        yaml_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
            "/app/src/data_ingestion/google_ads/google-ads.yaml",
            "/app/google-ads.yaml",
            os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
        ]
        
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"Loading credentials from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    developer_token = config.get('developer_token', developer_token)
                    client_id = config.get('client_id', client_id)
                    client_secret = config.get('client_secret', client_secret)
                    refresh_token = config.get('refresh_token', refresh_token)
                    customer_id = config.get('customer_id', customer_id) or config.get('login_customer_id', customer_id)
                    break
        
        # Ensure customer_id is a string without dashes
        customer_id = str(customer_id).replace('-', '')
        logger.info(f"Using customer ID: {customer_id}")
        
        # Get access token
        token_url = "https://accounts.google.com/o/oauth2/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        logger.info("Requesting OAuth2 access token...")
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            logger.error(f"Failed to get access token: {token_response.text}")
            return []
        
        access_token = token_response.json().get("access_token")
        logger.info("Successfully obtained access token")
        
        # Try the alternative AWQL format (older format that might work with older API versions)
        report_download_url = "https://adwords.google.com/api/adwords/reportdownload/v201809"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developerToken": developer_token,
            "clientCustomerId": customer_id,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # AWQL query format
        awql_query = f"""
            SELECT CampaignId, CampaignName, Impressions, Clicks, Cost, Date
            FROM CAMPAIGN_PERFORMANCE_REPORT
            WHERE Date BETWEEN '{start_date.replace('-', '')}'
            AND '{end_date.replace('-', '')}'
        """
        
        data = {
            "__rdquery": awql_query,
            "__fmt": "JSON"
        }
        
        logger.info(f"Making AWQL report API request to {report_download_url}")
        response = requests.post(report_download_url, headers=headers, data=data)
        
        if response.status_code != 200:
            logger.warning(f"AWQL report API request failed: {response.status_code}")
            logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars to avoid huge logs
            return []
        
        # Process the response
        try:
            # Try to parse as JSON first
            try:
                response_json = response.json()
                results = []
                
                # Check if we have results in the AWQL format
                if "report" in response_json:
                    report = response_json.get("report", {})
                    rows = report.get("rows", [])
                    
                    for row in rows:
                        row_data = {
                            "campaign_id": row.get("CampaignId", ""),
                            "campaign_name": row.get("CampaignName", ""),
                            "impressions": int(row.get("Impressions", 0)),
                            "clicks": int(row.get("Clicks", 0)),
                            "cost_micros": int(float(row.get("Cost", 0)) * 1000000),  # Convert to micros
                            "date": row.get("Date", "")
                        }
                        
                        results.append(row_data)
                
                logger.info(f"Successfully fetched {len(results)} rows of Google Ads data via report fetcher approach")
                return results
            except ValueError:
                # If not JSON, try to parse as CSV
                import csv
                from io import StringIO
                
                csv_data = StringIO(response.text)
                reader = csv.DictReader(csv_data)
                results = []
                
                for row in reader:
                    row_data = {
                        "campaign_id": row.get("Campaign ID", ""),
                        "campaign_name": row.get("Campaign", ""),
                        "impressions": int(row.get("Impressions", 0)),
                        "clicks": int(row.get("Clicks", 0)),
                        "cost_micros": int(float(row.get("Cost", 0)) * 1000000),  # Convert to micros
                        "date": row.get("Day", "")
                    }
                    
                    results.append(row_data)
                
                logger.info(f"Successfully fetched {len(results)} rows of Google Ads data via report fetcher approach (CSV)")
                return results
                
        except Exception as e:
            logger.error(f"Error processing report fetcher API response: {str(e)}")
            return []
        
    except Exception as e:
        logger.error(f"Error fetching Google Ads data via report fetcher approach: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def fetch_google_ads_data_fallback(start_date, end_date):
    """
    Fallback method to fetch data from Google Ads API.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Attempting to fetch Google Ads data via fallback from {start_date} to {end_date}...")
    
    try:
        # Try the v11 special auth first
        logger.info("Trying v11 special auth fallback...")
        results = fetch_google_ads_data_v11_special_auth(start_date, end_date)
        
        if not results:
            # Try the v11 specific fallback
            logger.info("v11 special auth fallback failed, trying v11 specific fallback...")
            results = fetch_google_ads_data_v11_fallback(start_date, end_date)
            
            if not results:
                # Try the REST API fallback
                logger.info("v11 specific fallback failed, trying REST API fallback...")
                results = fetch_google_ads_data_rest_fallback(start_date, end_date)
                
                if not results:
                    # Try the discovery document fallback
                    logger.info("REST API fallback failed, trying discovery document fallback...")
                    results = fetch_google_ads_data_discovery_fallback(start_date, end_date)
                    
                    if not results:
                        # Try the direct HTTP fallback
                        logger.info("Discovery document fallback failed, trying direct HTTP fallback...")
                        results = fetch_google_ads_data_direct_fallback(start_date, end_date)
                        
                        if not results:
                            # Last resort: try the report fetcher approach
                            logger.info("Direct HTTP fallback failed, trying report fetcher approach...")
                            results = fetch_google_ads_data_report_fetcher_fallback(start_date, end_date)
        
        return results
    except Exception as e:
        logger.error(f"Error in fallback method: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def fetch_google_ads_data(start_date, end_date):
    """
    Fetch data from Google Ads API for the specified date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        List[Dict]: List of campaign performance data dictionaries
    """
    logger.info(f"Fetching Google Ads data from {start_date} to {end_date}...")
    
    # Print debug information
    debug_google_ads_environment()
    
    client = get_google_ads_client()
    if not client:
        logger.error("Failed to create Google Ads client. Aborting data fetch.")
        return fetch_google_ads_data_fallback(start_date, end_date)
    
    # Try different API versions explicitly
    api_versions = ["v11", "v14", "v16", "v18", "v21"]
    
    for api_version in api_versions:
        logger.info(f"Trying to fetch Google Ads data with API version {api_version}")
        
        try:
            # Explicitly import the version-specific service
            if api_version == "v11":
                from google.ads.googleads.v11.services.services.google_ads_service import GoogleAdsServiceClient
            elif api_version == "v14":
                from google.ads.googleads.v14.services.services.google_ads_service import GoogleAdsServiceClient
            elif api_version == "v16":
                from google.ads.googleads.v16.services.services.google_ads_service import GoogleAdsServiceClient
            elif api_version == "v18":
                from google.ads.googleads.v18.services.services.google_ads_service import GoogleAdsServiceClient
            elif api_version == "v21":
                from google.ads.googleads.v21.services.services.google_ads_service import GoogleAdsServiceClient
            else:
                # Skip if we can't import the specific version
                logger.warning(f"Skipping API version {api_version} - no direct import available")
                continue
            
            # Get the customer ID
            customer_id = GOOGLE_ADS_CUSTOMER_ID
            
            # Try to load from YAML if available
            yaml_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
                "/app/src/data_ingestion/google_ads/google-ads.yaml",
                "/app/google-ads.yaml",
                os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
            ]
            
            for path in yaml_paths:
                if os.path.exists(path):
                    with open(path, 'r') as file:
                        config = yaml.safe_load(file)
                        customer_id = config.get('customer_id', customer_id) or config.get('login_customer_id', customer_id)
                        break
            
            # Ensure customer_id is a string
            customer_id = str(customer_id)
            logger.info(f"Using customer ID: {customer_id}")
            
            # Create the service client
            google_ads_service = client.get_service("GoogleAdsService", version=api_version)
            
            # Try different query formats
            query_formats = [
                # Format 1: Standard Google Ads Query Language (GAQL)
                f"""
                    SELECT
                      campaign.id,
                      campaign.name,
                      metrics.impressions,
                      metrics.clicks,
                      metrics.cost_micros,
                      segments.date
                    FROM campaign
                    WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                """,
                # Format 2: Alternative syntax with date range
                f"""
                    SELECT
                      campaign.id,
                      campaign.name,
                      metrics.impressions,
                      metrics.clicks,
                      metrics.cost_micros,
                      segments.date
                    FROM campaign
                    WHERE segments.date >= '{start_date}' AND segments.date <= '{end_date}'
                """,
                # Format 3: Simplified query
                f"""
                    SELECT
                      campaign.id,
                      campaign.name,
                      metrics.impressions,
                      metrics.clicks,
                      metrics.cost_micros,
                      segments.date
                    FROM campaign
                """
            ]
            
            for i, query in enumerate(query_formats):
                try:
                    logger.info(f"Executing query format {i+1} with API version {api_version}")
                    
                    # Execute the query
                    search_request = client.get_type("SearchGoogleAdsRequest", version=api_version)
                    search_request.customer_id = customer_id
                    search_request.query = query
                    
                    # Make the request
                    response = google_ads_service.search(request=search_request)
                    
                    # Process the results
                    results = []
                    for row in response:
                        try:
                            # Extract data from the row
                            campaign = row.campaign
                            metrics = row.metrics
                            segments = row.segments
                            
                            # Create a dictionary with the data
                            row_data = {
                                "campaign_id": campaign.id,
                                "campaign_name": campaign.name,
                                "impressions": metrics.impressions,
                                "clicks": metrics.clicks,
                                "cost_micros": metrics.cost_micros,
                                "date": segments.date
                            }
                            
                            results.append(row_data)
                        except Exception as e:
                            logger.warning(f"Error processing row: {str(e)}")
                            continue
                    
                    logger.info(f"Successfully fetched {len(results)} rows of Google Ads data with API version {api_version}")
                    return results
                except Exception as e:
                    logger.warning(f"Query format {i+1} failed with API version {api_version}: {str(e)}")
                    continue
        except Exception as e:
            logger.warning(f"Failed to use API version {api_version}: {str(e)}")
            continue
    
    # If all API versions failed, try the fallback methods
    logger.warning("All API versions failed. Trying fallback methods.")
    return fetch_google_ads_data_fallback(start_date, end_date)

def process_google_ads_data(raw_data):
    """
    Process raw data from Google Ads API into a format suitable for database storage.
    
    Args:
        raw_data (List[Dict]): Raw data from Google Ads API
        
    Returns:
        List[Dict]: Processed data ready for database insertion
    """
    logger.info(f"Processing {len(raw_data)} rows of Google Ads data")
    
    processed_data = []
    
    for row in raw_data:
        # Convert cost from micros (millionths of the account currency) to actual currency value
        cost_micros = row.get('cost_micros', 0)
        cost = float(cost_micros) / 1000000.0 if cost_micros else 0.0
        
        # Create a processed row
        processed_row = {
            'date': row.get('date'),
            'campaign_id': str(row.get('campaign_id')),  # Ensure campaign_id is a string
            'campaign_name': row.get('campaign_name'),
            'budget_amount_micros': row.get('budget_amount_micros', 0),
            'impressions': int(row.get('impressions', 0)),
            'clicks': int(row.get('clicks', 0)),
            'cost': cost,  # Converted from micros
            'conversions': row.get('conversions', 0),
            'created_at': datetime.now()
        }
        
        processed_data.append(processed_row)
    
    logger.info(f"Processed {len(processed_data)} rows of Google Ads data")
    return processed_data

def store_google_ads_data(processed_data):
    """
    Store processed Google Ads data in the database.
    
    Args:
        processed_data (List[Dict]): Processed data ready for database insertion
        
    Returns:
        int: Number of records affected
    """
    if not processed_data:
        logger.warning("No data to store")
        return 0
    
    logger.info(f"Storing {len(processed_data)} records in the database...")
    
    try:
        # Get database engine
        if not engine:
            logger.error("No database engine available")
            return 0
        
        # Create a connection
        with engine.connect() as conn:
            # Check if the table exists, create it if not
            if not conn.dialect.has_table(conn, 'sm_fact_google_ads'):
                logger.info("Creating sm_fact_google_ads table...")
                conn.execute(text("""
                    CREATE TABLE public.sm_fact_google_ads (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        campaign_id VARCHAR(255) NOT NULL,
                        campaign_name VARCHAR(255) NOT NULL,
                        budget_amount_micros BIGINT DEFAULT 0,
                        impressions INT DEFAULT 0,
                        clicks INT DEFAULT 0,
                        cost DECIMAL(12,2) DEFAULT 0,
                        conversions DECIMAL(12,2) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT sm_fact_google_ads_date_campaign_id_key UNIQUE (date, campaign_id)
                    )
                """))
                logger.info("sm_fact_google_ads table created successfully")
            else:
                # Check if we need to add the budget_amount_micros column
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'sm_fact_google_ads' AND column_name = 'budget_amount_micros'
                """))
                if not result.fetchone():
                    logger.info("Adding budget_amount_micros column to sm_fact_google_ads table...")
                    conn.execute(text("""
                        ALTER TABLE public.sm_fact_google_ads 
                        ADD COLUMN budget_amount_micros BIGINT DEFAULT 0
                    """))
                    logger.info("budget_amount_micros column added successfully")
                    
                # Check if we need to add the conversions column
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'sm_fact_google_ads' AND column_name = 'conversions'
                """))
                if not result.fetchone():
                    logger.info("Adding conversions column to sm_fact_google_ads table...")
                    conn.execute(text("""
                        ALTER TABLE public.sm_fact_google_ads 
                        ADD COLUMN conversions DECIMAL(12,2) DEFAULT 0
                    """))
                    logger.info("conversions column added successfully")
            
            # Begin a transaction
            trans = conn.begin()
            
            try:
                # Insert data
                records_affected = 0
                
                # Check if the table has the unique constraint
                constraint_query = text("""
                    SELECT COUNT(*) FROM pg_constraint 
                    WHERE conrelid = 'public.sm_fact_google_ads'::regclass 
                    AND contype = 'u'
                """)
                
                has_constraint = False
                try:
                    has_constraint = conn.execute(constraint_query).scalar() > 0
                except Exception as e:
                    logger.warning(f"Could not check for constraint: {str(e)}")
                
                # If no constraint exists, add one
                if not has_constraint:
                    logger.info("Adding unique constraint to sm_fact_google_ads table")
                    try:
                        conn.execute(text("""
                            ALTER TABLE public.sm_fact_google_ads 
                            ADD CONSTRAINT sm_fact_google_ads_date_campaign_id_key 
                            UNIQUE (date, campaign_id)
                        """))
                        logger.info("Added unique constraint")
                    except Exception as e:
                        logger.warning(f"Could not add constraint: {str(e)}")
                
                # Use a more robust insert approach that works with or without the constraint
                for row in processed_data:
                    try:
                        # First check if the record exists
                        check_query = text("""
                            SELECT id FROM public.sm_fact_google_ads
                            WHERE date = :date AND campaign_id = :campaign_id
                        """)
                        existing_id = conn.execute(check_query, {
                            'date': row['date'],
                            'campaign_id': row['campaign_id']
                        }).scalar()
                        
                        if existing_id:
                            # Update existing record
                            update_stmt = text("""
                                UPDATE public.sm_fact_google_ads
                                SET 
                                    campaign_name = :campaign_name,
                                    budget_amount_micros = :budget_amount_micros,
                                    impressions = :impressions,
                                    clicks = :clicks,
                                    cost = :cost,
                                    conversions = :conversions,
                                    created_at = :created_at
                                WHERE id = :id
                            """)
                            result = conn.execute(update_stmt, {**row, 'id': existing_id})
                        else:
                            # Insert new record
                            insert_stmt = text("""
                                INSERT INTO public.sm_fact_google_ads 
                                (date, campaign_id, campaign_name, budget_amount_micros, impressions, clicks, cost, conversions, created_at)
                                VALUES (:date, :campaign_id, :campaign_name, :budget_amount_micros, :impressions, :clicks, :cost, :conversions, :created_at)
                            """)
                            result = conn.execute(insert_stmt, row)
                        
                        records_affected += 1
                    except Exception as e:
                        logger.error(f"Error inserting/updating row: {str(e)}")
                        logger.error(f"Row data: {row}")
                
                # Commit the transaction
                trans.commit()
                logger.info(f"Successfully stored {records_affected} records")
                return records_affected
                
            except Exception as e:
                # Rollback the transaction on error
                trans.rollback()
                logger.error(f"Error storing Google Ads data: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return 0
                
    except Exception as e:
        logger.error(f"Error connecting to database for storing Google Ads data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def run_google_ads_etl(days=7):
    """
    Run the full ETL process for Google Ads data.
    
    Args:
        days (int): Number of days to fetch data for
    """
    logger.info(f"Starting Google Ads ETL process for the last {days} days...")
    
    try: # Add top-level try block
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Format dates as strings
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Date range: {start_date_str} to {end_date_str}")
        
        # Fetch data from Google Ads API (includes REST fallback if gRPC fails)
        # Auth errors inside fetch_google_ads_data should update status directly
        raw_data = fetch_google_ads_data(start_date_str, end_date_str)
        
        # If fetch returns None or empty due to non-auth error, we might still be 'ok'
        # but if it returns None due to auth error caught inside, status is already 'error'
        if raw_data is None: # Check specifically for None if fetch indicates critical failure
            logger.error("Fetching Google Ads data failed critically.")
            # Status should have been set by the failing function
            return False # Indicate failure
        elif not raw_data:
            logger.warning("No data fetched from Google Ads API (might be normal).")
            # Assume auth is ok if we got here without errors from fetch
            update_system_status('google_ads_auth_status', 'ok')
            return True # Indicate process ran, even if no data
        
        # Process the data
        processed_data = process_google_ads_data(raw_data)
        
        # Store in database
        records_affected = store_google_ads_data(processed_data)
        
        # Update status on successful completion (even if no records affected)
        update_system_status('google_ads_auth_status', 'ok')
        
        if records_affected > 0:
            logger.info(f"Successfully completed Google Ads ETL process, affected {records_affected} records")
            return True # Indicate success
        else:
            logger.warning("No records affected in the database, but process completed without auth errors.")
            return True # Still indicate success as the process ran
            
    except RefreshError as re:
        # Catch RefreshError specifically if it bubbles up here
        logger.error(f"Google Ads Refresh Token Error during ETL: {str(re)}")
        logger.error(traceback.format_exc())
        update_system_status('google_ads_auth_status', 'error: refresh token invalid')
        return False # Indicate failure
    except Exception as e:
        # Catch any other unexpected errors during the ETL process
        logger.error(f"Unexpected error during Google Ads ETL: {str(e)}")
        logger.error(traceback.format_exc())
        # Update status, assuming it might be auth related if not caught earlier
        update_system_status('google_ads_auth_status', f'error: {str(e)}')
        return False # Indicate failure
        return False

def backfill_google_ads_data(start_date_str, end_date_str=None):
    """
    Backfill Google Ads data for a date range.
    
    Args:
        start_date_str (str): Start date in YYYY-MM-DD format
        end_date_str (str, optional): End date in YYYY-MM-DD format. Defaults to today.
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Starting Google Ads backfill process from {start_date_str} to {end_date_str or 'today'}")
        
        # Set end date to today if not provided
        if not end_date_str:
            end_date_str = datetime.now().strftime('%Y-%m-%d')
            
        # Fetch data from API
        raw_data = fetch_google_ads_data(start_date_str, end_date_str)
        
        if not raw_data:
            logger.warning(f"No data fetched from Google Ads API for date range {start_date_str} to {end_date_str}")
            return False
        
        # Process the data
        processed_data = process_google_ads_data(raw_data)
        
        # Store in database
        records_affected = store_google_ads_data(processed_data)
        
        if records_affected > 0:
            logger.info(f"Successfully completed Google Ads backfill, affected {records_affected} records")
            return True
        else:
            logger.warning("No records affected in the database during backfill")
            return False
        
    except Exception as e:
        logger.error(f"Error running Google Ads backfill: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def setup_scheduled_tasks():
    """Set up scheduled tasks for Google Ads data fetching."""
    import schedule
    import time
    import threading
    
    logger.info("Setting up scheduled tasks for Google Ads data fetching")
    
    # Function to run in a separate thread
    def run_scheduled_job():
        logger.info("Starting scheduled Google Ads ETL job")
        # Fetch data to JSON
        fetch_and_save(days_back=3)
        # Wait a bit to ensure file is saved
        time.sleep(5)
        # Import latest file to database
        import_latest_json()
    
    # Function to import the latest JSON file
    def import_latest_json():
        try:
            # Find the latest JSON file in the data directory
            import glob
            import os
            
            data_dir = os.path.join(os.getcwd(), "data")
            files = glob.glob(os.path.join(data_dir, "google_ads_data_*.json"))
            
            if not files:
                logger.warning("No JSON files found in data directory")
                return
            
            # Sort by modification time (newest first)
            latest_file = max(files, key=os.path.getmtime)
            logger.info(f"Found latest JSON file: {latest_file}")
            
            # Import to database
            from import_from_json import import_google_ads_data
            records = import_google_ads_data(latest_file)
            logger.info(f"Imported {records} records from {latest_file}")
            
        except Exception as e:
            logger.error(f"Error importing latest JSON file: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Function to fetch data and save to JSON
    def fetch_and_save(days_back=3):
        try:
            from datetime import datetime, timedelta
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            from fetch_to_json import fetch_and_save as fetch_to_json_save
            filepath = fetch_to_json_save(start_date_str, end_date_str)
            
            if filepath:
                logger.info(f"Successfully fetched and saved Google Ads data to {filepath}")
            else:
                logger.warning("Failed to fetch and save Google Ads data")
                
        except Exception as e:
            logger.error(f"Error fetching and saving Google Ads data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def run_threaded(job_func):
        job_thread = threading.Thread(target=job_func)
        job_thread.start()
    
    # Schedule job to run every 4 hours
    schedule.every(4).hours.do(run_threaded, run_scheduled_job)
    
    # Also run once at startup
    run_threaded(run_scheduled_job)
    
    # Run the scheduler in a separate thread
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("Scheduled tasks set up successfully (running every 4 hours)")
    
    return scheduler_thread

def debug_google_ads_environment():
    """Debug function to print information about the Google Ads API environment."""
    logger.info("Debugging Google Ads environment...")
    
    # Print Python version
    import sys
    logger.info(f"Python version: {sys.version}")
    
    # Print installed packages
    import pkg_resources
    logger.info("Installed packages:")
    for pkg in pkg_resources.working_set:
        logger.info(f"  {pkg.project_name}=={pkg.version}")
    
    # Print environment variables (redacted)
    logger.info("Environment variables (redacted):")
    env_vars = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID"
    ]
    for var in env_vars:
        value = os.environ.get(var, "Not set")
        if value != "Not set":
            # Redact sensitive information
            value = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
        logger.info(f"  {var}: {value}")
    
    # Print YAML file paths
    yaml_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-ads.yaml'),
        "/app/src/data_ingestion/google_ads/google-ads.yaml",
        "/app/google-ads.yaml",
        os.path.join(os.getcwd(), "src/data_ingestion/google_ads/google-ads.yaml")
    ]
    logger.info("YAML file paths:")
    for path in yaml_paths:
        exists = os.path.exists(path)
        logger.info(f"  {path}: {'Exists' if exists else 'Does not exist'}")
        if exists:
            try:
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    # Print keys in the YAML file (redact values)
                    logger.info(f"    Keys in YAML file: {list(config.keys())}")
                    # Print API version if present
                    if 'api_version' in config:
                        logger.info(f"    API version in YAML: {config['api_version']}")
                    elif 'version' in config:
                        logger.info(f"    API version in YAML: {config['version']}")
            except Exception as e:
                logger.error(f"    Error reading YAML file: {str(e)}")
    
    # Check if we can import the Google Ads client
    logger.info("Checking Google Ads client imports:")
    try:
        from google.ads.googleads.client import GoogleAdsClient
        logger.info("  Successfully imported GoogleAdsClient")
        
        # Try to import version-specific clients
        versions = ["v11", "v14", "v16", "v18", "v21"]
        for version in versions:
            try:
                if version == "v11":
                    from google.ads.googleads.v11 import GoogleAdsClient as V11Client
                    logger.info(f"  Successfully imported GoogleAdsClient for {version}")
                elif version == "v14":
                    from google.ads.googleads.v14 import GoogleAdsClient as V14Client
                    logger.info(f"  Successfully imported GoogleAdsClient for {version}")
                elif version == "v16":
                    from google.ads.googleads.v16 import GoogleAdsClient as V16Client
                    logger.info(f"  Successfully imported GoogleAdsClient for {version}")
                elif version == "v18":
                    from google.ads.googleads.v18 import GoogleAdsClient as V18Client
                    logger.info(f"  Successfully imported GoogleAdsClient for {version}")
                elif version == "v21":
                    from google.ads.googleads.v21 import GoogleAdsClient as V21Client
                    logger.info(f"  Successfully imported GoogleAdsClient for {version}")
            except ImportError as e:
                logger.warning(f"  Failed to import GoogleAdsClient for {version}: {str(e)}")
    except ImportError as e:
        logger.error(f"  Failed to import GoogleAdsClient: {str(e)}")
    
    # Check network connectivity to Google Ads API
    logger.info("Checking network connectivity to Google Ads API:")
    try:
        import socket
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("googleads.googleapis.com", 443))
        logger.info("  Successfully connected to googleads.googleapis.com:443")
    except Exception as e:
        logger.error(f"  Failed to connect to googleads.googleapis.com:443: {str(e)}")
    
    # Try to get an access token
    logger.info("Trying to get an access token:")
    try:
        # Get credentials from environment variables or YAML
        client_id = GOOGLE_ADS_CLIENT_ID
        client_secret = GOOGLE_ADS_CLIENT_SECRET
        refresh_token = GOOGLE_ADS_REFRESH_TOKEN
        
        # Try to load from YAML if available
        for path in yaml_paths:
            if os.path.exists(path):
                logger.info(f"  Loading credentials from YAML: {path}")
                with open(path, 'r') as file:
                    config = yaml.safe_load(file)
                    client_id = config.get('client_id', client_id)
                    client_secret = config.get('client_secret', client_secret)
                    refresh_token = config.get('refresh_token', refresh_token)
                    break
        
        # Get access token
        token_url = "https://accounts.google.com/o/oauth2/token"
        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        logger.info("  Requesting OAuth2 access token...")
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code == 200:
            logger.info("  Successfully obtained access token")
            # Print token expiry
            token_json = token_response.json()
            if 'expires_in' in token_json:
                logger.info(f"  Token expires in: {token_json['expires_in']} seconds")
        else:
            logger.error(f"  Failed to get access token: {token_response.status_code}")
            logger.error(f"  Response: {token_response.text}")
    except Exception as e:
        logger.error(f"  Error getting access token: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("Google Ads environment debugging complete")

def main():
    """Main entry point for the Google Ads connector."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Google Ads ETL Service')
    parser.add_argument('--run-once', action='store_true', help='Run ETL process once and exit')
    parser.add_argument('--days', type=int, default=30, help='Number of days of data to fetch (default: 30)')
    parser.add_argument('--interval', type=int, default=6, help='Hours between ETL runs (default: 6)')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database engine
    engine = get_db_engine()
    
    if not engine:
        logger.error("Failed to initialize database engine. Exiting.")
        sys.exit(1)
    
    # If run-once flag is set, run ETL process once and exit
    if args.run_once:
        logger.info("Running Google Ads ETL process once...")
        try:
            debug_google_ads_environment()
            run_google_ads_etl(days=args.days)
            logger.info("ETL process completed successfully.")
        except Exception as e:
            logger.error(f"Error running ETL process: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(0)
    
    # Otherwise, run as a service with scheduled ETL runs
    logger.info(f"Starting Google Ads ETL service with {args.interval} hour interval")
    
    # Run ETL process immediately
    try:
        debug_google_ads_environment()
        run_google_ads_etl(days=args.days)
        logger.info("Initial ETL process completed successfully.")
    except Exception as e:
        logger.error(f"Error running initial ETL process: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Schedule ETL process to run at regular intervals
    schedule.every(args.interval).hours.do(run_google_ads_etl, days=args.days)
    
    # Keep the script running and check for scheduled jobs
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Service stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error in scheduler loop: {str(e)}")
            time.sleep(300)  # Wait 5 minutes before retrying on error

if __name__ == "__main__":
    import sys
    sys.exit(main())
