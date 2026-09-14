import time
import hashlib
import requests
from fyers_apiv3 import fyersModel
from app.config.settings import settings
from app.database import repository

# Fyers refresh token endpoint
FYERS_REFRESH_URL = "https://api-t1.fyers.in/api/v3/validate-refresh-token"

def get_valid_fyers_token() -> str:
    """
    Returns a valid access token.
    If the current access token is expired, it uses the refresh token to get a new one.
    If the refresh token is expired or fails, it throws an error indicating manual login is required.
    """
    tokens = repository.get_fyers_tokens()
    
    if not tokens:
        raise Exception("Authentication required. Please visit /api/auth/login to authenticate with FYERS.")
        
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    access_expiry = tokens["access_token_expires_at"]
    refresh_expiry = tokens["refresh_token_expires_at"]
    
    current_time = time.time()
    
    # 1. Check if the access token is still valid (add a 5-minute buffer)
    if current_time < (access_expiry - 300):
        return access_token
        
    # 2. Access token expired. Check if the refresh token is still valid
    if current_time >= refresh_expiry:
        raise Exception("Refresh token permanently expired (15-day limit). Manual login at /api/auth/login required.")
        
    # 3. Attempt to refresh the access token
    print("Access token expired. Attempting to refresh using refresh_token...")
    
    # Generate appIdHash = SHA256(client_id : secret_key)
    app_id_hash = hashlib.sha256(f"{settings.fyers_client_id}:{settings.fyers_secret_key}".encode()).hexdigest()
    
    payload = {
        "grant_type": "refresh_token",
        "appIdHash": app_id_hash,
        "refresh_token": refresh_token,
        "pin": "1234" # Pin is technically required by the schema even if unused in standard OAuth flow
    }
    
    try:
        response = requests.post(FYERS_REFRESH_URL, json=payload)
        data = response.json()
        
        if data.get("s") == "ok":
            new_access_token = data.get("access_token")
            # Some refresh flows rotate the refresh token. If FYERS doesn't, we keep the old one.
            # But the 15-day expiry clock stays ticking unless FYERS resets it.
            # We assume a new access token is valid for 24 hours.
            new_access_expiry = time.time() + (24 * 3600)
            
            repository.save_fyers_tokens(
                access_token=new_access_token,
                refresh_token=refresh_token,
                access_expiry=new_access_expiry,
                refresh_expiry=refresh_expiry
            )
            
            print("Successfully refreshed FYERS access token.")
            return new_access_token
        else:
            print(f"FYERS Refresh API rejected the token. Message: {data.get('message')}")
            raise Exception("Refresh failed due to FYERS rejection. Manual login required.")
            
    except requests.exceptions.RequestException as e:
        # Network error. Do not force re-auth, just fail the scan and try again next time.
        raise Exception(f"Network error while trying to refresh token: {str(e)}")

def get_fyers_model_dynamic() -> fyersModel.FyersModel:
    """
    Returns an initialized FyersModel instance using a guaranteed valid token.
    """
    token = get_valid_fyers_token()
    return fyersModel.FyersModel(
        client_id=settings.fyers_client_id,
        is_async=False, 
        token=token, 
        log_path=""
    )
