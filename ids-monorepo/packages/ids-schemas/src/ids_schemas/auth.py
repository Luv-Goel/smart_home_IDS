"""Authentication schemas for Smart Home IDS.

This module provides Pydantic models for authentication and authorization.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UserRole(str, Enum):
    """User role levels."""

    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    READONLY = "READONLY"
    EDGE_NODE = "EDGE_NODE"


class UserPermissions(BaseModel):
    """Permissions for a user role."""

    model_config = {'extra': 'allow'}

    # Alert permissions
    view_alerts: bool = True
    acknowledge_alerts: bool = False
    resolve_alerts: bool = False
    create_watchlist: bool = False

    # Device permissions
    view_devices: bool = True
    view_device_details: bool = True
    block_device: bool = False
    trust_device: bool = False

    # Configuration permissions
    view_config: bool = True
    edit_config: bool = False
    upload_model: bool = False

    # User management permissions
    view_users: bool = False
    create_users: bool = False
    edit_users: bool = False
    delete_users: bool = False

    # System permissions
    view_logs: bool = True
    access_api: bool = True
    access_websocket: bool = True


class UserRolePermissions(BaseModel):
    """Role to permissions mapping."""

    ADMIN: UserPermissions = Field(default_factory=lambda: UserPermissions(
        view_alerts=True,
        acknowledge_alerts=True,
        resolve_alerts=True,
        create_watchlist=True,
        view_devices=True,
        view_device_details=True,
        block_device=True,
        trust_device=True,
        view_config=True,
        edit_config=True,
        upload_model=True,
        view_users=True,
        create_users=True,
        edit_users=True,
        delete_users=True,
        view_logs=True,
        access_api=True,
        access_websocket=True,
    ))

    ANALYST: UserPermissions = Field(default_factory=lambda: UserPermissions(
        view_alerts=True,
        acknowledge_alerts=True,
        resolve_alerts=True,
        create_watchlist=True,
        view_devices=True,
        view_device_details=True,
        block_device=False,
        trust_device=True,
        view_config=True,
        edit_config=False,
        upload_model=False,
        view_users=False,
        create_users=False,
        edit_users=False,
        delete_users=False,
        view_logs=True,
        access_api=True,
        access_websocket=True,
    ))

    READONLY: UserPermissions = Field(default_factory=lambda: UserPermissions(
        view_alerts=True,
        acknowledge_alerts=False,
        resolve_alerts=False,
        create_watchlist=False,
        view_devices=True,
        view_device_details=True,
        block_device=False,
        trust_device=False,
        view_config=True,
        edit_config=False,
        upload_model=False,
        view_users=False,
        create_users=False,
        edit_users=False,
        delete_users=False,
        view_logs=True,
        access_api=True,
        access_websocket=True,
    ))

    EDGE_NODE: UserPermissions = Field(default_factory=lambda: UserPermissions(
        view_alerts=True,
        acknowledge_alerts=False,
        resolve_alerts=False,
        create_watchlist=False,
        view_devices=False,
        view_device_details=False,
        block_device=False,
        trust_device=False,
        view_config=True,
        edit_config=False,
        upload_model=False,
        view_users=False,
        create_users=False,
        edit_users=False,
        delete_users=False,
        view_logs=False,
        access_api=False,
        access_websocket=False,
    ))


class UserCredentials(BaseModel):
    """User login credentials."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class RegisterCredentials(BaseModel):
    """User registration credentials."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    email: str = Field(pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    role: UserRole = Field(default=UserRole.ANALYST)


class AuthToken(BaseModel):
    """Authentication token response."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="Bearer")
    expires_in: int = Field(description="Access token expiration in seconds")
    user_role: UserRole = Field(description="User's role")
    user_id: str = Field(description="User ID")
    username: str = Field(description="Username")


class RefreshTokenRequest(BaseModel):
    """Request to refresh authentication token."""

    refresh_token: str = Field(description="Refresh token")


class TokenPayload(BaseModel):
    """JWT token payload contents."""

    sub: str = Field(description="Subject (user ID)")
    username: str = Field(description="Username")
    role: UserRole = Field(description="User role")
    exp: int = Field(description="Expiration timestamp")
    iat: int = Field(description="Issued at timestamp")