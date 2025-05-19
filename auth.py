import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pydantic import BaseModel

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])

# Load client secrets from file
CLIENT_SECRETS_FILE = "client_secrets.json"
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

# Store tokens in memory (in production, use a database)
tokens = {}

class TokenData(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]

def create_flow():
    """Create OAuth flow from client secrets file"""
    # Use environment variable to determine the appropriate redirect URI
    redirect_uri = os.environ.get(
        "OAUTH_REDIRECT_URI", 
        "http://127.0.0.1:8000/auth/callback"  # Default for development
    )
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

@router.get("/login")
async def login():
    """Redirect user to Google OAuth consent screen"""
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # In production, store state in a secure session
    return RedirectResponse(authorization_url)

@router.get("/callback")
async def callback(request: Request):
    """Process OAuth callback from Google"""
    flow = create_flow()
    
    # Get authorization code from callback request
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code missing"
        )
    
    # Set environment variable to allow scope changes
    # This prevents the warning from becoming an exception
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    try:
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store tokens (in production, associate with user ID)
        user_id = "default_user"  # In production, get from authenticated user
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
        
        # Redirect to frontend or return token
        return {
            "message": "Authentication successful",
            "user_info": user_info,
            "token": user_id,  # In production, use a proper JWT
            "scopes_granted": credentials.scopes  # Show which scopes were granted
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

def get_credentials(user_id: str = "default_user") -> Credentials:
    """Get stored credentials for user"""
    if user_id not in tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    token_data = tokens[user_id]
    return Credentials(
        token=token_data.access_token,
        refresh_token=token_data.refresh_token,
        token_uri=token_data.token_uri,
        client_id=token_data.client_id,
        client_secret=token_data.client_secret,
        scopes=token_data.scopes
    )

# Dependency for protected routes
async def get_current_user(request: Request):
    """Verify token and return user_id"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    token = auth_header.split(" ")[1]
    if token not in tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return token  # user_id

