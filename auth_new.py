import json
import os
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

from fastapi import APIRouter, Depends, HTTPException, Request, status, Response, Cookie
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from pydantic import BaseModel
from uuid import UUID, uuid4

class TokenData(BaseModel):
    """Data model for storing OAuth tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    token_uri: str
    client_id: str
    client_secret: str
    scopes: List[str]

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])

# Define OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# Dictionary to store tokens (in production, use a database)
tokens: Dict[str, TokenData] = {}

# Simple API key authentication
API_KEY = os.environ.get("API_KEY", "your-default-api-key")

def verify_api_key(request: Request) -> Optional[str]:
    """Verify API key from header or query parameter"""
    # Check header first
    api_key = request.headers.get("X-API-Key")
    
    # If not in header, check query parameter
    if not api_key:
        api_key = request.query_params.get("api_key")
    
    # If no API key is provided, use application credentials
    if not api_key:
        return None
    
    # Verify the key if provided
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Return a user identifier for this API key
    return "api_user"

def get_credentials(user_id: str = None) -> Credentials:
    """Get stored credentials for user or application"""
    # If user_id is None or not provided, return application credentials from env vars
    if user_id is None:
        # Check if environment variables are set
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
        token_uri = os.environ.get("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")
        
        if not all([client_id, client_secret, refresh_token]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Application credentials not found. Set environment variables in .env file or run setup first."
            )
        
        # Create credentials from environment variables
        return Credentials(
            token=None,  # Token will be fetched using the refresh token
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
    
    # If user_id is provided, return user-specific credentials
    if user_id not in tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # Return user-specific credentials from tokens dictionary
    token_data = tokens[user_id]
    return Credentials(
        token=token_data.access_token,
        refresh_token=token_data.refresh_token,
        token_uri=token_data.token_uri,
        client_id=token_data.client_id,
        client_secret=token_data.client_secret,
        scopes=token_data.scopes
    )

def create_flow():
    """Create OAuth flow from environment variables"""
    # Get client configuration from environment variables
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/auth/admin/callback")
    
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google client credentials not found in environment variables"
        )
    
    # Create client config dictionary
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [redirect_uri]
        }
    }
    
    # Create flow from client config
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

# Admin-only endpoint to set up initial credentials
@router.get("/admin/setup")
async def admin_setup():
    """One-time setup to authenticate the application account"""
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store state for verification in callback
    return RedirectResponse(authorization_url)

@router.get("/admin/callback")
async def admin_callback(request: Request):
    """Process OAuth callback and store credentials temporarily"""
    flow = create_flow()
    
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code missing"
        )
    
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store as default_user token for the current session
        user_id = "default_user"
        tokens[user_id] = TokenData(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )
        
        # Get user info
        user_info = get_user_info(credentials)
        
        return {
            "message": "Authentication successful",
            "user_info": user_info,
            "token": user_id,
            "scopes_granted": credentials.scopes,
            "note": "These credentials are temporary for this session only. For production, add these to your .env file:",
            "env_variables": {
                "GOOGLE_CLIENT_ID": credentials.client_id,
                "GOOGLE_CLIENT_SECRET": credentials.client_secret,
                "GOOGLE_REFRESH_TOKEN": credentials.refresh_token,
                "GOOGLE_TOKEN_URI": credentials.token_uri
            }
            # "Admin Setup Successful!"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )

def get_user_info(credentials):
    """Get user info from Google"""
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    return user_info

# Dependency for protected routes
async def get_current_user(request: Request) -> Optional[str]:
    """Verify authentication and return user_id"""
    # Try Authorization header first (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        if token in tokens:
            return token
    
    # Try API key next
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if api_key and api_key == API_KEY:
        return "api_user"
    
    # If no valid authentication is provided, use application credentials
    return None

@router.get("/login")
async def login():
    """Redirect to admin setup for authentication"""
    return RedirectResponse(url="/auth/admin/setup")


6



