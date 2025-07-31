"""
Authentication routes for Google OAuth.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Optional
import secrets
import jwt
from datetime import datetime, timedelta
import requests
import json
import os
from urllib.parse import urlencode

# Local imports
from backend.models.database import get_db
from backend.models.user import User, OAuthToken
from backend.config.auth_config import get_google_oauth_settings, GoogleOAuthSettings
from backend.api.auth.dependencies import get_current_user

def create_jwt_token(data: dict) -> str:
    """
    Create a JWT token with the given payload data.

    Args:
        data: Dictionary containing the payload data for the JWT

    Returns:
        JWT token as a string
    """
    # Get settings for JWT configuration
    settings = get_google_oauth_settings()

    # Add expiration time to payload
    expiration = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    payload = data.copy()
    payload.update({"exp": expiration.timestamp()})

    # Create JWT token
    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return token

# Create a router
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@router.get("/user")
async def get_user_info(user: User = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    This endpoint is used by the frontend to check if the user is authenticated.
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "is_active": user.is_active,
        "is_admin": user.is_admin if hasattr(user, 'is_admin') else False
    }


@router.get("/login")
async def login(
    request: Request,
    settings: GoogleOAuthSettings = Depends(get_google_oauth_settings),
):
    """
    Initiate the Google OAuth login flow.
    """
    print("[DEBUG] Login endpoint called, initiating OAuth flow")
    # Generate a state token to prevent CSRF
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    # Build the authorization URL
    auth_params = {
        "client_id": settings.CLIENT_ID,
        "redirect_uri": settings.REDIRECT_URI,
        "scope": " ".join(settings.SCOPES),
        "response_type": "code",
        "state": state,
        "access_type": "offline",  # for refresh token
        "prompt": "consent",  # force consent screen for refresh token
    }
    
    auth_url = f"{settings.AUTHORIZATION_ENDPOINT}?{urlencode(auth_params)}"
    print(f"[DEBUG] Redirecting to Google OAuth: {auth_url[:50]}...")
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: GoogleOAuthSettings = Depends(get_google_oauth_settings),
):
    """
    Handle the OAuth callback from Google.
    This endpoint receives the authorization code after the user authenticates with Google.
    """
    print(f"[DEBUG] Callback received from Google OAuth with code: {code[:15]}... and state: {state[:10]}...")
    
    # Check if this code has been processed before (using a simple in-memory cache as demonstration)
    # In production, you would use Redis or another shared cache
    processed_codes_key = "processed_oauth_codes"
    processed_codes = request.session.get(processed_codes_key, [])
    
    if code in processed_codes:
        print(f"[DEBUG] This authorization code has already been processed! Code: {code[:15]}...")
        # Return a specific error or try to return the user directly
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code has already been used. Please try logging in again."
        )
    
    # Add this code to the processed list
    processed_codes.append(code)
    request.session[processed_codes_key] = processed_codes
    
    # Verify state token to prevent CSRF
    session_state = request.session.get("oauth_state")
    print(f"[DEBUG] Session state: {session_state[:10] if session_state else None}...")
    
    if state != session_state:
        print(f"[DEBUG] State mismatch! Received: {state[:10]}..., Session: {session_state[:10] if session_state else None}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )
    
    # Set the correct redirect URI - MUST match exactly what's registered in Google OAuth
    # Note: When testing, make sure this exactly matches what's in Google OAuth console
    redirect_uri = settings.REDIRECT_URI
    print(f"[DEBUG] Using redirect URI: {redirect_uri}")
    
    # Exchange authorization code for tokens
    token_data = {
        "code": code,
        "client_id": settings.CLIENT_ID,
        "client_secret": settings.CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    print(f"[DEBUG] Token exchange parameters: client_id={settings.CLIENT_ID[:5]}..., redirect_uri={redirect_uri}")
    print(f"[DEBUG] Full token request data: {json.dumps(token_data, indent=2)}")
    # Add detailed logging for the request
    print(f"[DEBUG] Sending token request to: {settings.TOKEN_ENDPOINT}")
    
    token_response = requests.post(
        settings.TOKEN_ENDPOINT,
        data=token_data,
    )
    print(f"[DEBUG] Token response status code: {token_response.status_code}")
    
    if token_response.status_code != 200:
        error_text = token_response.text
        print(f"[DEBUG] Token exchange failed: {token_response.status_code}")
        print(f"[DEBUG] Error response: {error_text}")
        
        # Try to parse error details if it's JSON
        try:
            error_json = token_response.json()
            print(f"[DEBUG] Error details: {json.dumps(error_json, indent=2)}")
            
            if 'error' in error_json and error_json['error'] == 'invalid_grant':
                print("[DEBUG] Invalid grant error typically means:")
                print("  - The authorization code has already been used or expired")
                print("  - The redirect URI doesn't match exactly what's registered in Google Console")
                print("  - The client ID or secret is incorrect")
                print(f"  - Using redirect_uri: {redirect_uri}")
        except Exception as e:
            print(f"[DEBUG] Failed to parse error response as JSON: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get token: {error_text}",
        )
    
    token_json = token_response.json()
    
    # Get user info with the access token
    user_response = requests.get(
        settings.USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {token_json['access_token']}"},
    )
    
    if user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get user info: {user_response.text}",
        )
    
    user_info = user_response.json()
    
    # Find user by email or create new user
    user = db.query(User).filter(User.email == user_info["email"]).first()
    if not user:
        user = User(
            email=user_info["email"],
            name=user_info.get("name"),
            picture=user_info.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Update user's last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Save/update OAuth token
    token = db.query(OAuthToken).filter(
        OAuthToken.user_id == user.id,
        OAuthToken.provider == "google"
    ).first()
    
    if not token:
        token = OAuthToken(
            user_id=user.id,
            provider="google",
        )
        db.add(token)
    
    # Calculate token expiry
    expires_in = token_json.get("expires_in", 3600)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    # Update token fields using encryption
    token.set_access_token(token_json["access_token"])
    
    # Only update refresh token if provided
    if "refresh_token" in token_json:
        token.set_refresh_token(token_json["refresh_token"])
        
    token.token_type = token_json["token_type"]
    token.expires_at = expires_at
    token.scopes = ",".join(settings.SCOPES)
    
    db.commit()
    
    # Generate a JWT session token
    session_token = create_jwt_token({"sub": user.email})
    
    # Create a response that sets a cookie and also returns the token
    token_data = {"sub": user.email}
    jwt_token = create_jwt_token(token_data)
    
    print(f"[DEBUG] Generated JWT token for user {user.email}: {jwt_token[:10]}...")
    # Determine if cookies should be secure based on request URL scheme
    secure_cookies = request.url.scheme == "https"
    print(f"[DEBUG] Cookie settings: httponly=True, secure={secure_cookies}, samesite=lax")
    
    # Create JSON response with the token for direct API use
    response = JSONResponse(content={
        "token": jwt_token,
        "user": {
            "email": user.email,
            "name": user.name,
            "picture": user.picture
        }
    })
    
    # Set the JWT token directly in a cookie as well (for API requests)
    response.set_cookie(
        key="auth_token",
        value=jwt_token,
        httponly=True,  # Can't be accessed by JavaScript for security
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        secure=secure_cookies,  # Based on request URL scheme
        samesite="lax"
    )
    
    # Also set a session_token cookie for backward compatibility
    response.set_cookie(
        key="session_token",
        value=jwt_token,  # Use the same JWT token for consistency
        httponly=True,
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
        secure=secure_cookies,  # Based on request URL scheme
        samesite="lax"
    )
    
    # Set CORS headers to ensure the cookies are accepted
    response.headers["Access-Control-Allow-Origin"] = settings.FRONTEND_URL
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    # Clear the oauth state from session
    request.session.pop("oauth_state", None)
    
    return response


@router.get("/refresh")
async def refresh_token(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: GoogleOAuthSettings = Depends(get_google_oauth_settings),
):
    """
    Refresh the OAuth token if it's expired.
    """
    # Get the user's token
    token = db.query(OAuthToken).filter(
        OAuthToken.user_id == user.id,
        OAuthToken.provider == "google"
    ).first()
    
    if not token or not token.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available",
        )
    
    # Only refresh if token is expired
    if not token.is_expired:
        return {"message": "Token is still valid"}
    
    # Request a new access token
    refresh_data = {
        "refresh_token": token.refresh_token,
        "client_id": settings.CLIENT_ID,
        "client_secret": settings.CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    
    token_response = requests.post(
        settings.TOKEN_ENDPOINT,
        data=refresh_data,
    )
    
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to refresh token: {token_response.text}",
        )
    
    token_json = token_response.json()
    
    # Calculate token expiry
    expires_in = token_json.get("expires_in", 3600)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    # Update token in database
    token.access_token = token_json["access_token"]
    token.expires_at = expires_at
    if "refresh_token" in token_json:
        token.refresh_token = token_json["refresh_token"]
    
    db.commit()
    
    return {"message": "Token refreshed successfully"}


@router.get("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log out the user by invalidating their session.
    """
    # Clear the session cookie
    response.delete_cookie(key="session_token")
    
    return {"message": "Logged out successfully"}


@router.get("/user")
async def get_user_info(user: User = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    """
    return {
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
    }


def create_jwt_token(data: dict) -> str:
    """
    Create a JWT token with the provided data.
    """
    settings = get_google_oauth_settings()
    expires_delta = timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: GoogleOAuthSettings = Depends(get_google_oauth_settings),
) -> User:
    """
    Decode the JWT token and get the current user.
    This is used as a dependency for protected routes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user
