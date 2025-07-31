"""
User models for authentication and session management.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import datetime
import json
from typing import Optional

from .database import Base
from backend.utils.encryption import encrypt_text, decrypt_text


class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationship with OAuth tokens
    oauth_tokens = relationship("OAuthToken", back_populates="user", cascade="all, delete-orphan")


class OAuthToken(Base):
    """OAuth token model for storing Google OAuth credentials."""
    
    __tablename__ = "oauth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String)  # e.g., "google"
    access_token = Column(String)  # This will store encrypted tokens
    refresh_token = Column(String)  # This will store encrypted tokens
    token_type = Column(String)
    expires_at = Column(DateTime)
    scopes = Column(String)  # Comma-separated list of scopes
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Encrypted access token handling
    @property
    def decrypted_access_token(self):
        """Get the decrypted access token."""
        if not self.access_token:
            return None
        return decrypt_text(self.access_token)
        
    def set_access_token(self, token):
        """Encrypt and set the access token."""
        if token:
            self.access_token = encrypt_text(token)
        else:
            self.access_token = None
    
    # Encrypted refresh token handling
    @property
    def decrypted_refresh_token(self):
        """Get the decrypted refresh token."""
        if not self.refresh_token:
            return None
        return decrypt_text(self.refresh_token)
        
    def set_refresh_token(self, token):
        """Encrypt and set the refresh token."""
        if token:
            self.refresh_token = encrypt_text(token)
        else:
            self.refresh_token = None
    
    # Relationship with User
    user = relationship("User", back_populates="oauth_tokens")
    
    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        if not self.expires_at:
            return True
        return datetime.datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict:
        """Convert token to dictionary format compatible with google.oauth2.credentials.Credentials."""
        return {
            "token": self.decrypted_access_token,
            "refresh_token": self.decrypted_refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": None,  # This will be filled from settings
            "client_secret": None,  # This will be filled from settings
            "scopes": self.scopes.split(",") if self.scopes else [],
            "expiry": self.expires_at.isoformat() if self.expires_at else None,
        }
