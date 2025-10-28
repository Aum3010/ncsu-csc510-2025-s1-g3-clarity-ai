"""
SuperTokens Authentication Service

This module handles SuperTokens initialization, configuration, and role management
for the document management application.
"""

import os
from functools import wraps
from typing import Dict, List, Optional, Callable, Any
from flask import request, jsonify, g
from supertokens_python import init, InputAppInfo, SupertokensConfig
from supertokens_python.recipe import passwordless, session, userroles, dashboard
from supertokens_python.recipe.passwordless import ContactEmailOnlyConfig
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.flask import verify_session
from supertokens_python.recipe.session.exceptions import (
    UnauthorisedError,
    InvalidClaimsError,
    TokenTheftError
)


def get_enhanced_session_config(app_config: Dict[str, str]) -> Dict[str, Any]:
    """
    Get enhanced session configuration with security features.

    Args:
        app_config: Application configuration dictionary

    Returns:
        Dictionary of session configuration parameters
    """
    # Use basic session configuration to avoid request context issues during initialization
    session_config = {
        'session_expired_status_code': 401,
        'invalid_claim_status_code': 403,
        'cookie_secure': app_config.get('api_domain', '').startswith('https'),
        'cookie_same_site': 'lax',
        'anti_csrf': 'VIA_TOKEN' if app_config.get('api_domain', '').startswith('https') else 'VIA_CUSTOM_HEADER',
        'get_token_transfer_method': lambda req, for_create_new_session, user_context: "cookie"
    }

    # Only add cookie domain if it's properly configured
    cookie_domain = app_config.get('cookie_domain')
    if cookie_domain and cookie_domain.strip():
        session_config['cookie_domain'] = cookie_domain

    older_cookie_domain = app_config.get('older_cookie_domain')
    if older_cookie_domain and older_cookie_domain.strip():
        session_config['older_cookie_domain'] = older_cookie_domain

    return session_config


def init_supertokens(app_config: Dict[str, str]) -> None:
    """
    Initialize SuperTokens with email-only OTP configuration.

    Args:
        app_config: Dictionary containing SuperTokens configuration values
    """
    init(
        app_info=InputAppInfo(
            app_name=app_config.get('app_name', 'Clarity AI'),
            api_domain=app_config.get('api_domain', 'http://localhost:5000'),
            website_domain=app_config.get(
                'website_domain', 'http://localhost:5173'),
            api_base_path="/auth",
            website_base_path="/auth"
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=app_config.get(
                'connection_uri', 'https://try.supertokens.com'),
            api_key=app_config.get('api_key')
        ),
        framework='flask',
        recipe_list=[
            # Email-only OTP passwordless authentication
            passwordless.init(
                contact_config=ContactEmailOnlyConfig(),
                flow_type="USER_INPUT_CODE"
            ),
            # Session management with enhanced security
            session.init(**get_enhanced_session_config(app_config)),
            # User roles and permissions
            userroles.init(),
            # Dashboard for admin management
            dashboard.init(
                api_key=app_config.get('api_key'),
                admins=[
                    # Admin emails from environment configuration
                    os.getenv('SUPERTOKENS_DASHBOARD_ADMIN_EMAIL',
                              'admin@example.com')
                ]
            )
        ],
        mode='asgi' if app_config.get('mode') == 'asgi' else 'wsgi'
    )


def get_roles_permissions_config() -> Dict[str, List[str]]:
    """
    Get the role and permission configuration for the application.

    Returns:
        Dictionary mapping role names to their associated permissions
    """
    return {
        "admin": [
            "api:*",
            "ui:*",
            "documents:*",
            "requirements:*",
            "summary:*",
            "users:*",
            "profile:*"
        ],
        "core-user": [
            "api:core",
            "ui:documents",
            "ui:requirements",
            "ui:overview",
            "documents:read",
            "documents:write",
            "requirements:read",
            "requirements:write",
            "summary:read",
            "summary:write",
            "profile:read",
            "profile:write"
        ],
        "pilot-user": [
            "api:basic",
            "ui:documents",
            "ui:requirements",
            "ui:overview",
            "documents:read",
            "documents:write",
            "requirements:read",
            "requirements:write",
            "summary:read",
            "summary:write",
            "profile:read",
            "profile:write"
        ]
    }


async def init_roles_and_permissions() -> None:
    """
    Initialize default roles and permissions in SuperTokens.
    This function should be called during application startup.

    Note: Role management requires SuperTokens Core with UserRoles recipe enabled.
    If not available, the application will use local role configuration only.
    """
    try:
        # Check if userroles module has the required methods
        if not hasattr(userroles, 'create_new_role_or_add_permissions') and not hasattr(userroles, 'create_role'):
            print(
                "SuperTokens UserRoles API not available - using local role configuration only")
            print(
                "Roles will be managed through application logic rather than SuperTokens Core")
            return

        roles_config = get_roles_permissions_config()
        print(f"Initializing {len(roles_config)} roles in SuperTokens...")

        # Create roles and assign permissions using available SuperTokens API
        for role_name, permissions in roles_config.items():
            try:
                # Try the newer API first
                if hasattr(userroles, 'create_new_role_or_add_permissions'):
                    await userroles.create_new_role_or_add_permissions(
                        role=role_name,
                        permissions=permissions
                    )

                # Fallback to older API
                elif hasattr(userroles, 'create_role'):
                    await userroles.create_role(role_name)
                    for permission in permissions:
                        await userroles.add_permission_to_role(role_name, permission)

            except Exception as e:
                print(f"⚠️  Could not create role '{role_name}': {str(e)}")
                continue

    except Exception as e:
        print(f"⚠️  Role initialization failed: {str(e)}")
        print("Application will continue with local role configuration")


def get_user_permissions(role: str) -> List[str]:
    """
    Get permissions for a specific role.

    Args:
        role: The role name

    Returns:
        List of permissions for the role
    """
    roles_config = get_roles_permissions_config()
    return roles_config.get(role, [])


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


# --- Authentication Decorators ---

def require_auth(required_permissions: Optional[List[str]] = None):
    """
    Decorator to require authentication and optionally check permissions with enhanced security.

    Args:
        required_permissions: List of permissions required to access the route

    Returns:
        Decorated function that verifies session and permissions
    """
    def decorator(f: Callable) -> Callable:
        @verify_session()
        def decorated_function(*args, **kwargs):
            try:
                # In Flask, @verify_session() stores the session in g.supertokens
                session = g.supertokens

                # Store session and user info in Flask's g object for route access
                g.session = session
                g.user_id = session.get_user_id()

                # Check permissions if required
                if required_permissions:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    user_permissions = loop.run_until_complete(
                        get_user_permissions_from_session(session))

                    for permission in required_permissions:
                        if not check_permission(user_permissions, permission):
                            return jsonify({
                                "error": "forbidden",
                                "message": f"Permission '{permission}' required"
                            }), 403

                # Call the original function with its expected arguments (not session)
                return f(*args, **kwargs)

            except (UnauthorisedError, InvalidClaimsError, TokenTheftError) as e:
                return jsonify({"message": "unauthorised"}), 401
            except Exception as e:
                print(f"Authentication error: {str(e)}")
                return jsonify({
                    "error": "authentication_error",
                    "message": str(e)
                }), 500

        # Preserve the original function's metadata
        decorated_function.__name__ = f.__name__
        decorated_function.__doc__ = f.__doc__
        return decorated_function
    return decorator


def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID from the Flask request context.

    Returns:
        User ID if authenticated, None otherwise
    """
    return getattr(g, 'user_id', None)


def get_current_session() -> Optional[SessionContainer]:
    """
    Get the current SuperTokens session from the Flask request context.

    Returns:
        SessionContainer if authenticated, None otherwise
    """
    return getattr(g, 'session', None)


async def get_user_permissions_from_session(session: SessionContainer) -> List[str]:
    """
    Get user permissions from SuperTokens session.

    Args:
        session: SuperTokens session container

    Returns:
        List of user permissions
    """
    try:
        user_id = session.get_user_id()

        # Since UserRoles API is not available, assign default pilot-user role
        # In production, this should be retrieved from SuperTokens or database
        user_roles = ['pilot-user']  # Default role for all authenticated users

        # Collect all permissions from user roles
        all_permissions = []
        roles_config = get_roles_permissions_config()

        for role in user_roles:
            role_permissions = roles_config.get(role, [])
            all_permissions.extend(role_permissions)

        # Remove duplicates and return
        return list(set(all_permissions))

    except Exception as e:
        print(f"Error getting user permissions: {str(e)}")
        return []


def verify_session_permissions(required_permissions: List[str]) -> bool:
    """
    Verify that the current session has the required permissions.

    Args:
        required_permissions: List of permissions to check

    Returns:
        True if user has all required permissions, False otherwise
    """
    session = get_current_session()
    if not session:
        return False

    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        user_permissions = loop.run_until_complete(
            get_user_permissions_from_session(session))
        loop.close()

        for permission in required_permissions:
            if not check_permission(user_permissions, permission):
                return False

        return True

    except Exception as e:
        print(f"Error verifying session permissions: {str(e)}")
        return False


# --- Convenience Decorators for Common Permission Patterns ---

def require_admin():
    """Decorator to require admin permissions."""
    return require_auth(["api:*"])


def require_core_user():
    """Decorator to require core user permissions."""
    return require_auth(["api:core"])


def require_basic_access():
    """Decorator to require basic API access."""
    return require_auth(["api:basic"])
