import os
from fyers_apiv3 import fyersModel
from app.config.settings import settings

TOKEN_FILE = "fyers_token.txt"

def get_session_model() -> fyersModel.SessionModel:
    """Creates and returns a Fyers SessionModel instance."""
    return fyersModel.SessionModel(
        client_id=settings.fyers_client_id,
        secret_key=settings.fyers_secret_key,
        redirect_uri=settings.fyers_redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )

def get_auth_url() -> str:
    """Generates the FYERS v3 login URL using the official SDK."""
    session = get_session_model()
    return session.generate_authcode()

def generate_access_token(auth_code: str) -> str:
    """Exchanges the auth_code for an access_token and refresh_token, and saves them securely."""
    import time
    from app.database import repository
    
    session = get_session_model()
    session.set_token(auth_code)
    response = session.generate_token()
    
    if response.get("s") == "ok":
        access_token = response.get("access_token")
        refresh_token = response.get("refresh_token")
        
        if not access_token or not refresh_token:
            raise Exception(f"FYERS returned OK but missing tokens: {response}")
            
        # FYERS access tokens typically last 1 day. We set expiry to 24 hours from now.
        access_expiry = time.time() + (24 * 3600)
        # FYERS refresh tokens last 15 days.
        refresh_expiry = time.time() + (15 * 24 * 3600)
        
        success = repository.save_fyers_tokens(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expiry=access_expiry,
            refresh_expiry=refresh_expiry
        )
        
        if not success:
            raise Exception("Failed to securely save FYERS tokens to the database.")
            
        return access_token
    else:
        raise Exception(f"Failed to generate access token: {response}")
