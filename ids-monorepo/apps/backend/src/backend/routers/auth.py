"""Authentication router for Smart Home IDS.

This module provides authentication endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_async_session, User
from ids_schemas.auth import (
    AuthToken,
    UserCredentials,
    RegisterCredentials,
    UserRole,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash.

    Args:
        plain_password: Plain password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    return bcrypt.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash password.

    Args:
        password: Password to hash

    Returns:
        Hashed password
    """
    return bcrypt.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    secret_key: str = "your-secret-key-change-in-production",
    algorithm: str = "HS256",
) -> str:
    """Create JWT access token.

    Args:
        data: Token payload data
        expires_delta: Token expiration time
        secret_key: Secret key for signing
        algorithm: Signing algorithm

    Returns:
        JWT token string
    """
    from jose import jwt

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """Get current authenticated user.

    Args:
        token: JWT token
        db: Database session

    Returns:
        User object
    """
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            token,
            "your-secret-key-change-in-production",
            algorithms=["HS256"],
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user.

    Args:
        current_user: Current user

    Returns:
        Active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


@router.post("/login", response_model=AuthToken)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    """Login endpoint.

    Args:
        form_data: Login form data
        db: Database session

    Returns:
        Authentication token
    """
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(seconds=900),
    )
    refresh_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(seconds=86400),
    )

    return AuthToken(
        access_token=access_token,
        refresh_token=refresh_token,
        user_role=UserRole(user.role),
        user_id=str(user.id),
        username=user.username,
    )


@router.post("/register", response_model=AuthToken)
async def register(
    credentials: RegisterCredentials,
    db: AsyncSession = Depends(get_async_session),
):
    """Register endpoint.

    Args:
        credentials: Registration credentials
        db: Database session

    Returns:
        Authentication token
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.username == credentials.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == credentials.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        username=credentials.username,
        email=credentials.email,
        hashed_password=hash_password(credentials.password),
        role=credentials.role,
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(seconds=900),
    )
    refresh_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(seconds=86400),
    )

    return AuthToken(
        access_token=access_token,
        refresh_token=refresh_token,
        user_role=credentials.role,
        user_id=str(user.id),
        username=user.username,
    )


@router.get("/me", response_model=User)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user.

    Args:
        current_user: Current user

    Returns:
        Current user
    """
    return current_user


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
) -> AuthToken:
    """Refresh token endpoint.

    Args:
        refresh_token: Refresh token

    Returns:
        New authentication token
    """
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            refresh_token,
            "your-secret-key-change-in-production",
            algorithms=["HS256"],
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    access_token = create_access_token(
        data={"sub": username, "role": payload.get("role", "ANALYST")},
        expires_delta=timedelta(seconds=900),
    )

    return AuthToken(
        access_token=access_token,
        refresh_token=refresh_token,
        user_role=UserRole(payload.get("role", "ANALYST")),
        user_id="",
        username=username,
    )