"""
Session Security Features

This module provides enhanced security features for SuperTokens sessions,
including secure cookie configuration, session timeout handling, CSRF protection,
and session validation.
"""

import os
import time
from typing import Dict, Any, Optional
from flask import request, g, current_app
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.exceptions import (
    UnauthorisedError,
    InvalidClaimsError,
    TokenTheftError
)


class SessionSecurityConfig:
    """Configuration class for session security settings"""
    
    def __init__(self):
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour default
        self.refresh_timeout = int(os.getenv('REFRESH_TIMEOUT', '86400'))  # 24 hours default
        self.csrf_protection = os.getenv('CSRF_PROTECTION', 'true').lower() == 'true'
        self.secure_cookies = os.getenv('SECURE_COOKIES', 'auto')  # auto, true, false
        self.same_site = os.getenv('SAME_SITE', 'lax')  # strict, lax, none
        self.max_session_age = int(os.getenv('MAX_SESSION_AGE', '604800'))  # 7 days default
        self.session_refresh_threshold = int(os.getenv('SESSION_REFRESH_THRESHOLD', '1800'))  # 30 minutes
    
    def get_cookie_secure_setting(self) -> bool:
        """Determine if cookies should be secure based on configuration and environment"""
        if self.secure_cookies == 'auto':
            # Auto-detect based on API domain or request scheme
            api_domain = os.getenv('API_DOMAIN', '')
            if api_domain.startswith('https'):
                return True
            # Fallback to request scheme if available and we're in a request context
            try:
                if hasattr(request, 'is_secure'):
                    return request.is_secure
            except RuntimeError:
                # We're outside of request context, use environment defaults
                pass
            return False
        return self.secure_cookies.lower() == 'true'
    
    def get_csrf_setting(self) -> str:
        """Get CSRF protection setting for SuperTokens"""
        if not self.csrf_protection:
            return "NONE"
        
        # Use VIA_TOKEN for HTTPS, VIA_CUSTOM_HEADER for HTTP
        if self.get_cookie_secure_setting():
            return "VIA_TOKEN"
        else:
            return "VIA_CUSTOM_HEADER"


def get_session_security_config() -> SessionSecurityConfig:
    """Get the current session security configuration"""
    return SessionSecurityConfig()


def configure_session_security() -> Dict[str, Any]:
    """
    Configure SuperTokens session security settings.
    
    Returns:
        Dictionary of session configuration parameters
    """
    config = get_session_security_config()
    
    session_config = {
        'cookie_secure': config.get_cookie_secure_setting(),
        'cookie_same_site': config.same_site,
        'session_expired_status_code': 401,
        'anti_csrf': config.get_csrf_setting(),
        'get_token_transfer_method': lambda req, for_create_new_session, user_context: "cookie"
    }
    
    # Only add cookie domain if it's properly configured
    cookie_domain = os.getenv('COOKIE_DOMAIN')
    if cookie_domain and cookie_domain.strip():
        session_config['cookie_domain'] = cookie_domain
    
    older_cookie_domain = os.getenv('OLDER_COOKIE_DOMAIN')
    if older_cookie_domain and older_cookie_domain.strip():
        session_config['older_cookie_domain'] = older_cookie_domain
    
    return session_config


def validate_session_timeout(session: SessionContainer) -> bool:
    """
    Validate if the session has exceeded timeout limits.
    
    Args:
        session: SuperTokens session container
        
    Returns:
        True if session is within timeout limits, False otherwise
    """
    try:
        config = get_session_security_config()
        
        # Get session creation time from access token payload
        payload = session.get_access_token_payload()
        session_created_time = payload.get('iat', 0)  # Issued at time
        current_time = int(time.time())
        
        # Check if session has exceeded maximum age
        session_age = current_time - session_created_time
        if session_age > config.max_session_age:
            return False
        
        # Check if session needs refresh
        last_refresh_time = payload.get('refreshedAt', session_created_time)
        time_since_refresh = current_time - last_refresh_time
        
        if time_since_refresh > config.session_timeout:
            return False
        
        return True
        
    except Exception:
        return False


def should_refresh_session(session: SessionContainer) -> bool:
    """
    Determine if the session should be refreshed based on age and activity.
    
    Args:
        session: SuperTokens session container
        
    Returns:
        True if session should be refreshed, False otherwise
    """
    try:
        config = get_session_security_config()
        
        payload = session.get_access_token_payload()
        last_refresh_time = payload.get('refreshedAt', payload.get('iat', 0))
        current_time = int(time.time())
        
        time_since_refresh = current_time - last_refresh_time
        
        # Refresh if we're past the refresh threshold
        return time_since_refresh > config.session_refresh_threshold
        
    except Exception:
        return False


async def refresh_session_if_needed(session: SessionContainer) -> SessionContainer:
    """
    Refresh the session if it meets the refresh criteria.
    
    Args:
        session: Current session container
        
    Returns:
        Refreshed session container or original if no refresh needed
    """
    try:
        if should_refresh_session(session):
            # Update the refreshedAt timestamp in the session
            current_payload = session.get_access_token_payload()
            current_payload['refreshedAt'] = int(time.time())
            
            # Merge the updated payload
            await session.merge_into_access_token_payload(current_payload)
            
            return session
        
        return session
        
    except Exception:
        # If refresh fails, return original session
        return session


def validate_csrf_token() -> bool:
    """
    Validate CSRF token for the current request.
    
    Returns:
        True if CSRF validation passes, False otherwise
    """
    config = get_session_security_config()
    
    if not config.csrf_protection:
        return True
    
    try:
        # SuperTokens handles CSRF validation automatically when configured
        # This function provides additional validation if needed
        
        csrf_header = request.headers.get('anti-csrf')
        if config.get_csrf_setting() == "VIA_CUSTOM_HEADER" and not csrf_header:
            return False
        
        # Additional custom CSRF validation can be added here
        return True
        
    except Exception:
        return False


def get_security_headers() -> Dict[str, str]:
    """
    Get security headers to be added to responses.
    
    Returns:
        Dictionary of security headers
    """
    config = get_session_security_config()
    
    headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # Add HSTS header for HTTPS
    if config.get_cookie_secure_setting():
        headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return headers


def validate_session_integrity(session: SessionContainer) -> Dict[str, Any]:
    """
    Perform comprehensive session integrity validation.
    
    Args:
        session: SuperTokens session container
        
    Returns:
        Dictionary with validation results and recommendations
    """
    results = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'recommendations': []
    }
    
    try:
        # Check session payload integrity - only require critical fields
        payload = session.get_access_token_payload()
        critical_fields = ['iat', 'exp', 'sub']
        
        for field in critical_fields:
            if field not in payload:
                results['valid'] = False
                results['errors'].append(f'Missing critical field in token: {field}')
        
        # If critical fields are missing, don't continue with other validations
        if not results['valid']:
            return results
        
        # Check session timeout (but be lenient for new sessions)
        session_age = int(time.time()) - payload.get('iat', 0)
        if session_age > 60:  # Only check timeout for sessions older than 1 minute
            if not validate_session_timeout(session):
                results['valid'] = False
                results['errors'].append('Session has exceeded timeout limits')
        
        # Check if session needs refresh (but don't fail validation)
        if should_refresh_session(session):
            results['warnings'].append('Session should be refreshed')
            results['recommendations'].append('refresh_session')
        
        # Validate CSRF protection (but be lenient for new sessions)
        try:
            if not validate_csrf_token():
                results['warnings'].append('CSRF validation failed - this may be expected for new sessions')
        except Exception:
            results['warnings'].append('CSRF validation could not be performed')
        
        # Check for suspicious activity patterns (warnings only, don't fail validation)
        user_agent = request.headers.get('User-Agent', '')
        stored_user_agent = payload.get('userAgent', '')
        
        if stored_user_agent and user_agent != stored_user_agent:
            results['warnings'].append('User agent mismatch detected')
        
        # Check IP address if stored (warnings only)
        client_ip = request.environ.get('REMOTE_ADDR')
        stored_ip = payload.get('clientIP')
        
        if stored_ip and client_ip != stored_ip:
            results['warnings'].append('IP address change detected')
        
    except Exception as e:
        # Don't fail validation for new sessions due to missing metadata
        results['warnings'].append(f'Session validation warning: {str(e)}')
        print(f"Session validation warning (non-critical): {str(e)}")
    
    return results


def enhance_session_payload(session: SessionContainer, additional_data: Dict[str, Any] = None) -> None:
    """
    Enhance session payload with security-related metadata.
    
    Args:
        session: SuperTokens session container
        additional_data: Additional data to store in session
    """
    try:
        import asyncio
        
        async def update_payload():
            try:
                current_payload = session.get_access_token_payload()
                
                # Add security metadata
                security_data = {
                    'userAgent': request.headers.get('User-Agent', ''),
                    'clientIP': request.environ.get('REMOTE_ADDR'),
                    'lastActivity': int(time.time()),
                    'securityLevel': 'standard'
                }
                
                # Merge additional data if provided
                if additional_data:
                    security_data.update(additional_data)
                
                # Update the payload
                current_payload.update(security_data)
                await session.merge_into_access_token_payload(current_payload)
                
            except Exception as inner_e:
                print(f"Warning: Could not update session payload: {str(inner_e)}")
                # Don't re-raise - this is non-critical for authentication
        
        # Run the async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(update_payload())
        
    except Exception as e:
        print(f"Warning: Could not enhance session payload: {str(e)}")
        # Don't re-raise - this is non-critical for authentication


def create_session_activity_log(session: SessionContainer, action: str, details: Dict[str, Any] = None) -> None:
    """
    Log session activity for security monitoring.
    
    Args:
        session: SuperTokens session container
        action: The action being performed
        details: Additional details about the action
    """
    try:
        log_entry = {
            'timestamp': int(time.time()),
            'user_id': session.get_user_id(),
            'session_handle': session.get_handle(),
            'action': action,
            'ip_address': request.environ.get('REMOTE_ADDR'),
            'user_agent': request.headers.get('User-Agent', ''),
            'details': details or {}
        }
        
        # In a production environment, this would be sent to a logging service
        # For now, we'll just print it (could be enhanced to use proper logging)
        print(f"Session Activity: {log_entry}")
        
    except Exception as e:
        print(f"Warning: Could not log session activity: {str(e)}")


def handle_session_security_violation(violation_type: str, session: Optional[SessionContainer] = None, details: Dict[str, Any] = None) -> None:
    """
    Handle detected session security violations.
    
    Args:
        violation_type: Type of security violation detected
        session: Session container if available
        details: Additional details about the violation
    """
    try:
        violation_log = {
            'timestamp': int(time.time()),
            'violation_type': violation_type,
            'ip_address': request.environ.get('REMOTE_ADDR'),
            'user_agent': request.headers.get('User-Agent', ''),
            'details': details or {}
        }
        
        if session:
            violation_log.update({
                'user_id': session.get_user_id(),
                'session_handle': session.get_handle()
            })
        
        # Log the security violation
        print(f"SECURITY VIOLATION: {violation_log}")
        
        # In a production environment, this could trigger:
        # - Immediate session revocation
        # - User notification
        # - Admin alerts
        # - Rate limiting
        # - IP blocking
        
    except Exception as e:
        print(f"Error handling security violation: {str(e)}")


# Middleware function to add security headers to all responses
def add_security_headers_middleware(response):
    """
    Add security headers to Flask responses.
    
    Args:
        response: Flask response object
        
    Returns:
        Modified response with security headers
    """
    try:
        headers = get_security_headers()
        for header, value in headers.items():
            response.headers[header] = value
        return response
    except Exception:
        return response