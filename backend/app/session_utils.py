"""
Session Management Utilities

This module provides utility functions for managing SuperTokens sessions,
user context, and permission validation in the Flask application.
"""

import asyncio
from typing import Optional, List, Dict, Any
from flask import g, request, jsonify
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.exceptions import (
    UnauthorisedError,
    InvalidClaimsError,
    TokenTheftError
)
from supertokens_python.recipe import userroles


class SessionError(Exception):
    """Custom exception for session-related errors"""
    pass


class PermissionError(Exception):
    """Custom exception for permission-related errors"""
    pass


def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID from the Flask request context.

    Returns:
        User ID if authenticated, None otherwise

    Raises:
        SessionError: If session context is invalid
    """
    try:
        user_id = getattr(g, 'user_id', None)
        if user_id is None:
            # Try to extract from session if available
            session = get_current_session()
            if session:
                user_id = session.get_user_id()
                g.user_id = user_id  # Cache for subsequent calls
        return user_id
    except Exception as e:
        raise SessionError(f"Failed to get current user ID: {str(e)}")


def get_current_session() -> Optional[SessionContainer]:
    """
    Get the current SuperTokens session from the Flask request context.

    Returns:
        SessionContainer if authenticated, None otherwise

    Raises:
        SessionError: If session context is invalid
    """
    try:
        return getattr(g, 'session', None)
    except Exception as e:
        raise SessionError(f"Failed to get current session: {str(e)}")


def require_authenticated_user() -> str:
    """
    Ensure the current request has an authenticated user.

    Returns:
        User ID of the authenticated user

    Raises:
        SessionError: If user is not authenticated
    """
    user_id = get_current_user_id()
    if not user_id:
        raise SessionError("Authentication required")
    return user_id


def get_session_metadata() -> Dict[str, Any]:
    """
    Get metadata from the current session.

    Returns:
        Dictionary containing session metadata

    Raises:
        SessionError: If session is not available
    """
    session = get_current_session()
    if not session:
        raise SessionError("No active session")

    try:
        return {
            'user_id': session.get_user_id(),
            'session_handle': session.get_handle(),
            'tenant_id': session.get_tenant_id(),
            'access_token_payload': session.get_access_token_payload(),
            'session_data': session.get_session_data_from_database()
        }
    except Exception as e:
        raise SessionError(f"Failed to get session metadata: {str(e)}")


async def get_user_roles_async(user_id: str) -> List[str]:
    """
    Get user roles from SuperTokens asynchronously.

    Args:
        user_id: The user ID to get roles for

    Returns:
        List of role names assigned to the user

    Raises:
        PermissionError: If roles cannot be retrieved
    """
    try:
        roles_response = await userroles.get_roles_for_user(user_id)

        if hasattr(roles_response, 'roles'):
            return roles_response.roles
        else:
            return []

    except Exception as e:
        raise PermissionError(f"Failed to get user roles: {str(e)}")


def get_user_roles(user_id: str) -> List[str]:
    """
    Get user roles from SuperTokens synchronously.

    Args:
        user_id: The user ID to get roles for

    Returns:
        List of role names assigned to the user

    Raises:
        PermissionError: If roles cannot be retrieved
    """
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(get_user_roles_async(user_id))

    except Exception as e:
        raise PermissionError(f"Failed to get user roles: {str(e)}")


async def get_user_permissions_async(user_id: str) -> List[str]:
    """
    Get user permissions from SuperTokens roles asynchronously.

    Args:
        user_id: The user ID to get permissions for

    Returns:
        List of permissions assigned to the user through their roles

    Raises:
        PermissionError: If permissions cannot be retrieved
    """
    try:
        # Import here to avoid circular imports
        from .auth_service import get_roles_permissions_config

        user_roles = await get_user_roles_async(user_id)
        roles_config = get_roles_permissions_config()

        # Collect all permissions from user roles
        all_permissions = []
        for role in user_roles:
            role_permissions = roles_config.get(role, [])
            all_permissions.extend(role_permissions)

        # Remove duplicates and return
        return list(set(all_permissions))

    except Exception as e:
        raise PermissionError(f"Failed to get user permissions: {str(e)}")


def get_user_permissions(user_id: str) -> List[str]:
    """
    Get user permissions from SuperTokens roles synchronously.

    Args:
        user_id: The user ID to get permissions for

    Returns:
        List of permissions assigned to the user through their roles

    Raises:
        PermissionError: If permissions cannot be retrieved
    """
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(get_user_permissions_async(user_id))

    except Exception as e:
        raise PermissionError(f"Failed to get user permissions: {str(e)}")


def check_permission(user_permissions: List[str], required_permission: str) -> bool:
    """
    Check if user has the required permission.

    Args:
        user_permissions: List of user's permissions
        required_permission: The permission to check

    Returns:
        True if user has permission, False otherwise
    """
    # Check for wildcard permissions
    if "api:*" in user_permissions or "ui:*" in user_permissions:
        return True

    # Check for exact permission match
    if required_permission in user_permissions:
        return True

    # Check for wildcard match (e.g., "documents:*" covers "documents:read")
    permission_parts = required_permission.split(":")
    if len(permission_parts) == 2:
        wildcard_permission = f"{permission_parts[0]}:*"
        if wildcard_permission in user_permissions:
            return True

    return False


def verify_session_permissions(required_permissions: List[str]) -> bool:
    """
    Verify that the current session has the required permissions.

    Args:
        required_permissions: List of permissions to check

    Returns:
        True if user has all required permissions, False otherwise

    Raises:
        SessionError: If session is not available
        PermissionError: If permissions cannot be verified
    """
    try:
        user_id = require_authenticated_user()
        user_permissions = get_user_permissions(user_id)

        for permission in required_permissions:
            if not check_permission(user_permissions, permission):
                return False

        return True

    except SessionError:
        return False
    except Exception as e:
        raise PermissionError(f"Error verifying session permissions: {str(e)}")


def require_permissions(required_permissions: List[str]) -> None:
    """
    Ensure the current user has the required permissions.

    Args:
        required_permissions: List of permissions to check

    Raises:
        SessionError: If user is not authenticated
        PermissionError: If user lacks required permissions
    """
    user_id = require_authenticated_user()

    if not verify_session_permissions(required_permissions):
        user_permissions = get_user_permissions(user_id)
        missing_permissions = [
            perm for perm in required_permissions
            if not check_permission(user_permissions, perm)
        ]
        raise PermissionError(
            f"Missing required permissions: {', '.join(missing_permissions)}"
        )


def get_current_user_context() -> Dict[str, Any]:
    """
    Get comprehensive context about the current authenticated user.

    Returns:
        Dictionary containing user context information

    Raises:
        SessionError: If user is not authenticated
        PermissionError: If user context cannot be retrieved
    """
    try:
        user_id = require_authenticated_user()
        session = get_current_session()

        if not session:
            raise SessionError("No active session")

        # Get user roles and permissions
        user_roles = get_user_roles(user_id)
        user_permissions = get_user_permissions(user_id)

        return {
            'user_id': user_id,
            'session_handle': session.get_handle(),
            'tenant_id': session.get_tenant_id(),
            'roles': user_roles,
            'permissions': user_permissions,
            'access_token_payload': session.get_access_token_payload()
        }

    except (SessionError, PermissionError):
        raise
    except Exception as e:
        raise SessionError(f"Failed to get user context: {str(e)}")


def validate_session_integrity() -> bool:
    """
    Validate the integrity of the current session.

    Returns:
        True if session is valid and intact, False otherwise
    """
    try:
        session = get_current_session()
        if not session:
            return False

        # Basic validation - ensure we can get user ID
        user_id = session.get_user_id()
        if not user_id:
            return False

        # Ensure session handle exists
        handle = session.get_handle()
        if not handle:
            return False

        return True

    except (UnauthorisedError, InvalidClaimsError, TokenTheftError):
        return False
    except Exception:
        return False


def create_session_error_response(error: Exception) -> tuple:
    """
    Create a standardized error response for session-related errors.

    Args:
        error: The exception that occurred

    Returns:
        Tuple of (response_dict, status_code)
    """
    if isinstance(error, UnauthorisedError):
        return {
            "error": "unauthorized",
            "message": "Authentication required"
        }, 401
    elif isinstance(error, InvalidClaimsError):
        return {
            "error": "forbidden",
            "message": "Insufficient permissions",
            "details": {"invalid_claims": getattr(error, 'invalid_claims', [])}
        }, 403
    elif isinstance(error, TokenTheftError):
        return {
            "error": "token_theft",
            "message": "Session security violation detected"
        }, 401
    elif isinstance(error, SessionError):
        return {
            "error": "session_error",
            "message": str(error)
        }, 401
    elif isinstance(error, PermissionError):
        return {
            "error": "permission_error",
            "message": str(error)
        }, 403
    else:
        return {
            "error": "internal_error",
            "message": "An unexpected error occurred"
        }, 500


# Convenience functions for common permission patterns
def require_admin_access() -> None:
    """Ensure current user has admin access."""
    require_permissions(["api:*"])


def require_core_user_access() -> None:
    """Ensure current user has core user access."""
    require_permissions(["api:core"])


def require_basic_access() -> None:
    """Ensure current user has basic API access."""
    require_permissions(["api:basic"])


def can_access_documents(action: str = "read") -> bool:
    """Check if current user can access documents."""
    try:
        return verify_session_permissions([f"documents:{action}"])
    except:
        return False


def can_access_requirements(action: str = "read") -> bool:
    """Check if current user can access requirements."""
    try:
        return verify_session_permissions([f"requirements:{action}"])
    except:
        return False


def can_access_summary(action: str = "read") -> bool:
    """Check if current user can access project summary."""
    try:
        return verify_session_permissions([f"summary:{action}"])
    except:
        return False
