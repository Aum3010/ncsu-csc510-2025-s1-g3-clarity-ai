"""
Integration tests for Flask authentication with SuperTokens.

Tests end-to-end authentication flow, role-based access control across all protected routes,
and user profile creation and management workflows.
"""

import pytest
import json
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.models import UserProfile, Document, Requirement, ProjectSummary
from app.main import db

# Use fixtures from conftest.py - no need to redefine app and client

class TestFlaskAuthenticationIntegration:
    """Integration tests for Flask authentication with SuperTokens"""
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint works"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'Clarity AI API'
        assert 'timestamp' in data
    
    def test_authentication_configuration(self):
        """Test that authentication configuration is properly loaded"""
        from app.auth_service import get_roles_permissions_config
        
        config = get_roles_permissions_config()
        
        # Verify all expected roles exist
        expected_roles = ["admin", "core-user", "pilot-user"]
        for role in expected_roles:
            assert role in config
            assert isinstance(config[role], list)
            assert len(config[role]) > 0
        
        # Verify admin has wildcard permissions
        admin_perms = config["admin"]
        assert any("*" in perm for perm in admin_perms)
        
        # Verify core-user has appropriate permissions
        core_perms = config["core-user"]
        assert "api:core" in core_perms
        assert any("documents:" in perm for perm in core_perms)
        assert any("requirements:" in perm for perm in core_perms)
        
        # Verify pilot-user has limited permissions
        pilot_perms = config["pilot-user"]
        assert "api:basic" in pilot_perms
        assert any("documents:" in perm for perm in pilot_perms)
    
    def test_permission_checking_logic(self):
        """Test permission checking with various scenarios"""
        from app.auth_service import check_permission
        
        # Test exact permission match
        user_perms = ["documents:read", "requirements:write"]
        assert check_permission(user_perms, "documents:read") == True
        assert check_permission(user_perms, "requirements:write") == True
        assert check_permission(user_perms, "documents:delete") == False
        
        # Test wildcard permissions
        wildcard_perms = ["documents:*"]
        assert check_permission(wildcard_perms, "documents:read") == True
        assert check_permission(wildcard_perms, "documents:write") == True
        assert check_permission(wildcard_perms, "documents:delete") == True
        assert check_permission(wildcard_perms, "requirements:read") == False
        
        # Test admin wildcard
        admin_perms = ["api:*"]
        assert check_permission(admin_perms, "documents:read") == True
        assert check_permission(admin_perms, "requirements:write") == True
        assert check_permission(admin_perms, "summary:delete") == True
    
    @pytest.fixture
    def mock_session_admin(self):
        """Create mock SuperTokens session for admin user"""
        session = Mock()
        session.get_user_id.return_value = "admin_user_123"
        session.get_handle.return_value = "admin_session_handle"
        session.get_tenant_id.return_value = "public"
        session.get_access_token_payload.return_value = {
            'iat': 1640995200,
            'exp': 1640998800,
            'sub': 'admin_user_123',
            'refreshedAt': 1640995200,
            'userAgent': 'Test Browser',
            'clientIP': '127.0.0.1'
        }
        session.get_session_data_from_database.return_value = {}
        session.merge_into_access_token_payload = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_session_core_user(self):
        """Create mock SuperTokens session for core user"""
        session = Mock()
        session.get_user_id.return_value = "core_user_456"
        session.get_handle.return_value = "core_session_handle"
        session.get_tenant_id.return_value = "public"
        session.get_access_token_payload.return_value = {
            'iat': 1640995200,
            'exp': 1640998800,
            'sub': 'core_user_456',
            'refreshedAt': 1640995200,
            'userAgent': 'Test Browser',
            'clientIP': '127.0.0.1'
        }
        session.get_session_data_from_database.return_value = {}
        session.merge_into_access_token_payload = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_session_pilot_user(self):
        """Create mock SuperTokens session for pilot user"""
        session = Mock()
        session.get_user_id.return_value = "pilot_user_789"
        session.get_handle.return_value = "pilot_session_handle"
        session.get_tenant_id.return_value = "public"
        session.get_access_token_payload.return_value = {
            'iat': 1640995200,
            'exp': 1640998800,
            'sub': 'pilot_user_789',
            'refreshedAt': 1640995200,
            'userAgent': 'Test Browser',
            'clientIP': '127.0.0.1'
        }
        session.get_session_data_from_database.return_value = {}
        session.merge_into_access_token_payload = AsyncMock()
        return session
    
    def setup_mock_user_roles(self, user_id, roles):
        """Helper to set up mock user roles for SuperTokens"""
        async def mock_get_roles(uid):
            if uid == user_id:
                mock_response = Mock()
                mock_response.roles = roles
                return mock_response
            return Mock(roles=[])
        
        return mock_get_roles


class TestEndToEndAuthenticationFlow(TestFlaskAuthenticationIntegration):
    """Test complete authentication flow from login to protected resource access"""


class TestRoleBasedAccessControl(TestFlaskAuthenticationIntegration):
    """Test role-based access control across all protected routes"""


class TestUserProfileManagement(TestFlaskAuthenticationIntegration):
    """Test user profile creation and management workflows"""
    
    def test_create_user_profile_success(self, client, app):
        """Test successful user profile creation"""
        
        with app.app_context():
            profile_data = {
                'user_id': 'new_user_123',
                'email': 'newuser@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'company': 'Test Corp',
                'job_title': 'Developer'
            }
            
            # Mock role assignment
            with patch('app.routes.assign_default_role_to_user') as mock_assign_role:
                mock_assign_role.return_value = 'pilot-user'
                
                response = client.post('/api/auth/profile', 
                                     data=json.dumps(profile_data),
                                     content_type='application/json')
                
                assert response.status_code == 201
                data = response.get_json()
                
                assert data['message'] == 'Profile created successfully'
                assert data['profile']['user_id'] == 'new_user_123'
                assert data['profile']['email'] == 'newuser@example.com'
                assert data['profile']['first_name'] == 'John'
                assert data['profile']['last_name'] == 'Doe'
                assert data['profile']['company'] == 'Test Corp'
                assert data['profile']['job_title'] == 'Developer'
                assert data['profile']['remaining_tokens'] == 5
                assert data['profile']['assigned_role'] == 'pilot-user'
                
                # Verify profile was saved to database
                saved_profile = UserProfile.query.filter_by(user_id='new_user_123').first()
                assert saved_profile is not None
                assert saved_profile.email == 'newuser@example.com'
    
    def test_create_user_profile_missing_fields(self, client, app):
        """Test user profile creation with missing required fields"""
        
        with app.app_context():
            incomplete_data = {
                'user_id': 'incomplete_user',
                'email': 'incomplete@example.com'
                # Missing first_name, last_name, company, job_title
            }
            
            response = client.post('/api/auth/profile',
                                 data=json.dumps(incomplete_data),
                                 content_type='application/json')
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'Missing required field' in data['error']
    
    def test_create_duplicate_user_profile(self, client, app):
        """Test creating duplicate user profile fails"""
        
        with app.app_context():
            # Create initial profile
            profile = UserProfile(
                user_id='duplicate_user',
                email='duplicate@example.com',
                first_name='First',
                last_name='User',
                company='Company',
                job_title='Job'
            )
            db.session.add(profile)
            db.session.commit()
            
            # Try to create duplicate
            duplicate_data = {
                'user_id': 'duplicate_user',
                'email': 'different@example.com',
                'first_name': 'Second',
                'last_name': 'User',
                'company': 'Different Company',
                'job_title': 'Different Job'
            }
            
            response = client.post('/api/auth/profile',
                                 data=json.dumps(duplicate_data),
                                 content_type='application/json')
            
            assert response.status_code == 409
            data = response.get_json()
            assert data['error'] == 'Profile already exists for this user'
    
    def test_get_user_profile_success(self, client, app):
        """Test successful user profile retrieval"""
        
        with app.app_context():
            # Create test profile
            profile = UserProfile(
                user_id='get_user_123',
                email='getuser@example.com',
                first_name='Get',
                last_name='User',
                company='Get Company',
                job_title='Get Job'
            )
            db.session.add(profile)
            db.session.commit()
            
            response = client.get('/api/auth/profile?user_id=get_user_123')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['profile']['user_id'] == 'get_user_123'
            assert data['profile']['email'] == 'getuser@example.com'
            assert data['profile']['first_name'] == 'Get'
            assert data['profile']['last_name'] == 'User'
            assert data['profile']['company'] == 'Get Company'
            assert data['profile']['job_title'] == 'Get Job'
    
    def test_get_user_profile_not_found(self, client, app):
        """Test user profile retrieval for non-existent user"""
        
        with app.app_context():
            response = client.get('/api/auth/profile?user_id=nonexistent_user')
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Profile not found'
    
    def test_get_user_profile_missing_user_id(self, client, app):
        """Test user profile retrieval without user_id parameter"""
        
        with app.app_context():
            response = client.get('/api/auth/profile')
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'user_id parameter is required'


class TestSessionSecurityIntegration(TestFlaskAuthenticationIntegration):
    """Test session security features in integration scenarios"""
    

class TestHealthCheckEndpoints(TestFlaskAuthenticationIntegration):
    """Test health check endpoints for authentication system"""
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'Clarity AI API'
        assert 'timestamp' in data


class TestAuthenticatedEndpoints(TestFlaskAuthenticationIntegration):
    """Test authenticated endpoints with mocked authentication"""
    
    def create_mock_session(self, user_id, roles):
        """Helper to create mock SuperTokens session"""
        session = Mock()
        session.get_user_id.return_value = user_id
        session.get_handle.return_value = f"{user_id}_handle"
        session.get_tenant_id.return_value = "public"
        session.get_access_token_payload.return_value = {
            'iat': 1640995200,
            'exp': 1640998800,
            'sub': user_id,
            'refreshedAt': 1640995200,
            'userAgent': 'Test Browser',
            'clientIP': '127.0.0.1'
        }
        session.get_session_data_from_database.return_value = {}
        session.merge_into_access_token_payload = AsyncMock()
        return session
    
    def setup_mock_user_roles(self, user_id, roles):
        """Helper to set up mock user roles for SuperTokens"""
        async def mock_get_roles(uid):
            if uid == user_id:
                mock_response = Mock()
                mock_response.roles = roles
                return mock_response
            return Mock(roles=[])
        
        return mock_get_roles


class TestUserProfileIntegration(TestFlaskAuthenticationIntegration):
    """Test user profile management integration"""
    
    def test_create_user_profile_success(self, client, app):
        """Test successful user profile creation"""
        
        profile_data = {
            'user_id': 'new_user_123',
            'email': 'newuser@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'company': 'Test Corp',
            'job_title': 'Developer'
        }
        
        # Mock role assignment
        with patch('app.routes.assign_default_role_to_user') as mock_assign_role:
            mock_assign_role.return_value = 'pilot-user'
            
            response = client.post('/api/auth/profile', 
                                 data=json.dumps(profile_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            data = response.get_json()
            
            assert data['message'] == 'Profile created successfully'
            assert data['profile']['user_id'] == 'new_user_123'
            assert data['profile']['email'] == 'newuser@example.com'
            assert data['profile']['first_name'] == 'John'
            assert data['profile']['last_name'] == 'Doe'
            assert data['profile']['company'] == 'Test Corp'
            assert data['profile']['job_title'] == 'Developer'
            assert data['profile']['remaining_tokens'] == 5
            assert data['profile']['assigned_role'] == 'pilot-user'
    
    def test_create_user_profile_missing_fields(self, client, app):
        """Test user profile creation with missing required fields"""
        
        incomplete_data = {
            'user_id': 'incomplete_user',
            'email': 'incomplete@example.com'
            # Missing first_name, last_name, company, job_title
        }
        
        response = client.post('/api/auth/profile',
                             data=json.dumps(incomplete_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Missing required field' in data['error']
    
    def test_get_user_profile_success(self, client, app):
        """Test successful user profile retrieval"""
        
        # First create a profile
        profile_data = {
            'user_id': 'get_user_123',
            'email': 'getuser@example.com',
            'first_name': 'Get',
            'last_name': 'User',
            'company': 'Get Company',
            'job_title': 'Get Job'
        }
        
        with patch('app.routes.assign_default_role_to_user') as mock_assign_role:
            mock_assign_role.return_value = 'pilot-user'
            
            # Create the profile
            create_response = client.post('/api/auth/profile',
                                        data=json.dumps(profile_data),
                                        content_type='application/json')
            assert create_response.status_code == 201
            
            # Now retrieve it
            response = client.get('/api/auth/profile?user_id=get_user_123')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['profile']['user_id'] == 'get_user_123'
            assert data['profile']['email'] == 'getuser@example.com'
            assert data['profile']['first_name'] == 'Get'
            assert data['profile']['last_name'] == 'User'
            assert data['profile']['company'] == 'Get Company'
            assert data['profile']['job_title'] == 'Get Job'
    
    def test_get_user_profile_not_found(self, client, app):
        """Test user profile retrieval for non-existent user"""
        
        response = client.get('/api/auth/profile?user_id=nonexistent_user')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'Profile not found'
    
    def test_get_user_profile_missing_user_id(self, client, app):
        """Test user profile retrieval without user_id parameter"""
        
        response = client.get('/api/auth/profile')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'user_id parameter is required'


class TestErrorHandlingIntegration(TestFlaskAuthenticationIntegration):
    """Test error handling in authentication system"""
    
    def test_session_error_response_creation(self):
        """Test error response creation for different error types"""
        from app.session_utils import create_session_error_response, SessionError, PermissionError
        from supertokens_python.recipe.session.exceptions import (
            UnauthorisedError,
            InvalidClaimsError,
            TokenTheftError
        )
        
        # Test unauthorized error
        error = UnauthorisedError("Session expired")
        response, status_code = create_session_error_response(error)
        assert status_code == 401
        assert response['error'] == 'unauthorized'
        assert 'message' in response
        
        # Test forbidden error
        error = InvalidClaimsError("Invalid claims", [])
        response, status_code = create_session_error_response(error)
        assert status_code == 403
        assert response['error'] == 'forbidden'
        
        # Test token theft error
        error = TokenTheftError("Token theft", "handle", "user")
        response, status_code = create_session_error_response(error)
        assert status_code == 401
        assert response['error'] == 'token_theft'
        
        # Test session error
        error = SessionError("Custom session error")
        response, status_code = create_session_error_response(error)
        assert status_code == 401
        assert response['error'] == 'session_error'
        assert response['message'] == 'Custom session error'
        
        # Test permission error
        error = PermissionError("Missing permissions")
        response, status_code = create_session_error_response(error)
        assert status_code == 403
        assert response['error'] == 'permission_error'
        
        # Test generic error
        error = Exception("Unexpected error")
        response, status_code = create_session_error_response(error)
        assert status_code == 500
        assert response['error'] == 'internal_error'


class TestHealthCheckIntegration(TestFlaskAuthenticationIntegration):
    """Test health check endpoints integration"""
    
    def test_basic_health_check_detailed(self, client):
        """Test basic health check endpoint with detailed validation"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'Clarity AI API'
        assert 'timestamp' in data
        
        # Validate timestamp format
        from datetime import datetime
        try:
            datetime.fromisoformat(data['timestamp'])
        except ValueError:
            pytest.fail("Invalid timestamp format")
