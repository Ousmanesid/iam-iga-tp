"""Security utilities for authentication."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

DEMO_TOKEN = settings.DEMO_TOKEN


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user."""
    token = credentials.credentials
    
    # Demo mode: accept demo token
    if settings.DEMO_MODE and token == DEMO_TOKEN:
        return {"username": "demo", "role": "admin"}
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return {"username": username}
    except JWTError:
        raise credentials_exception


async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple auth check."""
    return await get_current_user(credentials)


class AuthService:
    """Authentication service."""
    
    def authenticate(self, username: str, password: str):
        """Authenticate a user."""
        # Demo mode
        if username == "demo" and password == "demo":
            return {"username": "demo", "role": "admin"}
        return None
    
    def create_token(self, user: dict):
        """Create an access token."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )


auth_service = AuthService()
