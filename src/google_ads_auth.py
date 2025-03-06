#!/usr/bin/env python
"""Google Ads API Authentication Helper.

This script helps you generate a new refresh token for the Google Ads API.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

def generate_refresh_token():
    """Generate a new refresh token for Google Ads API."""
    print("Google Ads API Authentication Helper")
    print("====================================")
    
    # Find the client secrets file
    client_secrets_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "credentials", "google_ads", "client_secrets.json"
    )
    
    if not os.path.exists(client_secrets_path):
        print(f"Could not find client_secrets.json at {client_secrets_path}")
        client_secrets_path = input("Please enter the full path to your client_secrets.json file: ")
    
    # Scopes required for Google Ads API
    scopes = ["https://www.googleapis.com/auth/adwords"]
    
    # Create a flow instance to manage the OAuth 2.0 Authorization Grant Flow steps
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_path,
        scopes=scopes
    )
    
    # Generate the URL to authorize and get the auth code
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    
    print(f"\n1. Visit this URL to authorize this application:")
    print(f"\n{auth_url}\n")
    print("2. After approval, copy the authorization code.")
    
    # Ask for the authorization code
    code = input("\nEnter the authorization code: ")
    
    try:
        # Exchange the auth code for credentials
        flow.fetch_token(code=code)
        
        # Get the refresh token
        refresh_token = flow.credentials.refresh_token
        
        if refresh_token:
            print("\nAuthentication successful!")
            print(f"\nYour new refresh token is: {refresh_token}\n")
            
            # Update the google-ads.yaml file
            yaml_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "credentials", "google_ads", "google-ads.yaml"
            )
            
            # Ask if user wants to update the yaml file
            update_yaml = input("\nDo you want to update your google-ads.yaml file with this token? (y/n): ").lower()
            
            if update_yaml == 'y':
                try:
                    # Read the current yaml file
                    with open(yaml_path, 'r') as file:
                        yaml_content = file.read()
                    
                    # Replace the refresh token
                    if 'refresh_token:' in yaml_content:
                        # Simple string replacement (not ideal but works for this purpose)
                        import re
                        new_yaml = re.sub(
                            r'refresh_token: "?[^"\n]+"?', 
                            f'refresh_token: "{refresh_token}"',
                            yaml_content
                        )
                        
                        # Write the updated yaml file
                        with open(yaml_path, 'w') as file:
                            file.write(new_yaml)
                        
                        print(f"Updated refresh token in {yaml_path}")
                    else:
                        print(f"Could not find refresh_token field in {yaml_path}")
                except Exception as e:
                    print(f"Error updating yaml file: {e}")
            
            print("\nYou can now use this refresh token in your Google Ads API calls.")
            return refresh_token
        else:
            print("\nFailed to get refresh token. Make sure you approved the consent screen.")
            return None
    except Exception as e:
        print(f"\nError exchanging authorization code: {e}")
        return None

if __name__ == "__main__":
    generate_refresh_token()
