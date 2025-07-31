"""
Authentication dependencies for FastAPI endpoints.
These dependencies can be used to protect API routes that require authentication.
"""
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from datetime import datetime

from backend.models.database import get_db
from backend.models.user import User
from backend.config.auth_config import get_google_oauth_settings

# HTTP Bearer scheme for token authentication
oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from the HTTP Authorization token or session cookie.
    This can be used as a dependency in FastAPI routes.
    
    Args:
        credentials: Optional Bearer token from Authorization header
        session_token: Optional token from session cookie
        db: Database session
        
    Returns:
        User object for the authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    # Setup our exception for failed auth
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from either the Authorization header or session cookie
    token = None
    if credentials:
        token = credentials.credentials
        print(f"[DEBUG] Found token in Authorization header: {token[:10] if token else None}...")
    elif session_token:
        token = session_token
        print(f"[DEBUG] Found token in cookie: {token[:10] if token else None}...")
    else:
        print("[DEBUG] No token found in Authorization header or cookie")
    
    if not token:
        print("[DEBUG] No authentication token provided")
        raise credentials_exception
    
    settings = get_google_oauth_settings()
    
    try:
        # Decode and validate JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
            
        # Check token expiration
        exp = payload.get("exp")
        if not exp or datetime.utcnow().timestamp() > exp:
            raise credentials_exception
            
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not user.is_active:
        raise credentials_exception
        
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    """Alias for get_current_user_from_token for cleaner imports and to avoid circular dependencies."""
    return await get_current_user_from_token(credentials, session_token, db)


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.
    This can be used for endpoints that work both for authenticated and unauthenticated users.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    try:
        # Get token from session cookie
        session_token = request.cookies.get("session_token")
        
        if not session_token:
            return None
            
        settings = get_google_oauth_settings()
        
        # Decode and validate JWT token
        payload = jwt.decode(
            session_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        email: str = payload.get("sub")
        if not email:
            return None
            
        # Check token expiration
        exp = payload.get("exp")
        if not exp or datetime.utcnow().timestamp() > exp:
            return None
            
        # Get user from database
        user = db.query(User).filter(User.email == email).first()
        return user
        
    except (jwt.PyJWTError, Exception):
        return None
