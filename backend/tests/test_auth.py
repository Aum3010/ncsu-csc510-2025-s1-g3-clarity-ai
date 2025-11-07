"""
Unit tests for authentication components.

Tests authentication decorators, session verification, profile management,
and user-scoped data filtering logic.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from flask import Flask, g, request
from app.main import create_app, db
from app.models import UserProfile, Document, Requirement, ProjectSummary
from app.auth_service import (
    init_supertokens,
    get_roles_permissions_config,
    check_permission,
    require_auth,
    get_current_user_id,
    get_current_session,
    get_user_permissions_from_session
)
from app.session_utils import (
    SessionError,
    PermissionError,
    get_user_roles,
    get_user_permissions,
    verify_session_permissions,
    require_permissions,
    get_current_user_context,
    validate_session_integrity,
    create_session_error_response
)
from app.session_security import (
    SessionSecurityConfig,
    validate_session_timeout,
    should_refresh_session,
    validate_csrf_token,
    validate_session_integrity as security_validate_session_integrity,
    enhance_session_payload
)


class TestAuthenticationDecorators:
    """Test authentication decorators and session verification"""
    
    # Use app fixture from conftest.py
    
    @pytest.fixture
    def mock_session(self):
        """Create mock SuperTokens session"""
        session = Mock()
        session.get_user_id.return_value = "test_user_123"
        session.get_handle.return_value = "session_handle_123"
        session.get_tenant_id.return_value = "public"
        session.get_access_token_payload.return_value = {
            'iat': 1640995200,
            'exp': 1640998800,
            'sub': 'test_user_123',
            'refreshedAt': 1640995200
        }
        return session
    
    def test_get_roles_permissions_config(self):
        """Test role and permission configuration retrieval"""
        config = get_roles_permissions_config()
        
        assert isinstance(config, dict)
        assert "admin" in config
        assert "core-user" in config
        assert "pilot-user" in config
        
        # Test admin permissions
        admin_perms = config["admin"]
        assert "api:*" in admin_perms
        assert "ui:*" in admin_perms
        
        # Test core-user permissions
        core_perms = config["core-user"]
        assert "api:core" in core_perms
        assert "documents:read" in core_perms
        assert "requirements:write" in core_perms
        
        # Test pilot-user permissions
        pilot_perms = config["pilot-user"]
        assert "api:basic" in pilot_perms
        assert "documents:read" in pilot_perms
    
    def test_check_permission_exact_match(self):
        """Test permission checking with exact matches"""
        user_permissions = ["documents:read", "requirements:write"]
        
        assert check_permission(user_permissions, "documents:read") == True
        assert check_permission(user_permissions, "requirements:write") == True
        assert check_permission(user_permissions, "documents:delete") == False
    
    def test_check_permission_wildcard(self):
        """Test permission checking with wildcards"""
        user_permissions = ["documents:*"]
        
        assert check_permission(user_permissions, "documents:read") == True
        assert check_permission(user_permissions, "documents:write") == True
        assert check_permission(user_permissions, "requirements:read") == False
        
        # Test api:* wildcard
        api_permissions = ["api:*"]
        assert check_permission(api_permissions, "api:core") == True
        assert check_permission(api_permissions, "documents:read") == True  # api:* covers everything
    
    def test_check_permission_admin_wildcard(self):
        """Test admin wildcard permissions"""
        user_permissions = ["api:*"]
        
        assert check_permission(user_permissions, "documents:read") == True
        assert check_permission(user_permissions, "requirements:write") == True
        assert check_permission(user_permissions, "summary:delete") == True
    
    def test_get_current_user_id_from_context(self, app):
        """Test getting current user ID from Flask context"""
        with app.app_context():
            with patch('app.auth_service.g') as mock_g:
                mock_g.user_id = "test_user_123"
                
                user_id = get_current_user_id()
                assert user_id == "test_user_123"
    
    def test_get_current_user_id_none(self, app):
        """Test getting current user ID when not set"""
        with app.app_context():
            with patch('app.auth_service.g') as mock_g:
                mock_g.user_id = None
                
                user_id = get_current_user_id()
                assert user_id is None
    
    def test_get_current_session_from_context(self, app, mock_session):
        """Test getting current session from Flask context"""
        with app.app_context():
            with patch('app.auth_service.g') as mock_g:
                mock_g.session = mock_session
                
                session = get_current_session()
                assert session == mock_session
    
    def test_get_current_session_none(self, app):
        """Test getting current session when not set"""
        with app.app_context():
            with patch('app.auth_service.g') as mock_g:
                mock_g.session = None
                
                session = get_current_session()
                assert session is None


class TestSessionUtils:
    """Test session utility functions"""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock SuperTokens session"""
        session = Mock()
        session.get_user_id.return_value = "test_user_123"
        session.get_handle.return_value = "session_handle_123"
        session.get_tenant_id.return_value = "public"
        session.get_access_token_payload.return_value = {
            'iat': 1640995200,
            'exp': 1640998800,
            'sub': 'test_user_123'
        }
        return session
    
    @patch('app.session_utils.get_current_user_id')
    def test_require_authenticated_user_success(self, mock_get_user_id):
        """Test requiring authenticated user when user is authenticated"""
        mock_get_user_id.return_value = "test_user_123"
        
        from app.session_utils import require_authenticated_user
        user_id = require_authenticated_user()
        assert user_id == "test_user_123"
    
    @patch('app.session_utils.get_current_user_id')
    def test_require_authenticated_user_failure(self, mock_get_user_id):
        """Test requiring authenticated user when user is not authenticated"""
        mock_get_user_id.return_value = None
        
        from app.session_utils import require_authenticated_user
        with pytest.raises(SessionError, match="Authentication required"):
            require_authenticated_user()
    
    @patch('app.session_utils.get_current_session')
    def test_get_session_metadata_success(self, mock_get_session, mock_session):
        """Test getting session metadata successfully"""
        mock_get_session.return_value = mock_session
        
        from app.session_utils import get_session_metadata
        metadata = get_session_metadata()
        
        assert metadata['user_id'] == "test_user_123"
        assert metadata['session_handle'] == "session_handle_123"
        assert metadata['tenant_id'] == "public"
        assert 'access_token_payload' in metadata
    
    @patch('app.session_utils.get_current_session')
    def test_get_session_metadata_no_session(self, mock_get_session):
        """Test getting session metadata when no session exists"""
        mock_get_session.return_value = None
        
        from app.session_utils import get_session_metadata
        with pytest.raises(SessionError, match="No active session"):
            get_session_metadata()
    
    @patch('app.session_utils.asyncio.get_event_loop')
    def test_get_user_roles_success(self, mock_get_loop):
        """Test getting user roles successfully"""
        # Mock event loop
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = ["core-user", "pilot-user"]
        mock_get_loop.return_value = mock_loop
        
        # Mock the async function
        async def mock_async_get_roles(user_id):
            return ["core-user", "pilot-user"]
        
        with patch('app.session_utils.get_user_roles_async', mock_async_get_roles):
            roles = get_user_roles("test_user_123")
            assert roles == ["core-user", "pilot-user"]



class TestProfileManagement:
    """Test user profile management functions"""
    
    # Use app and client fixtures from conftest.py
    
    def test_create_user_profile_success(self, app):
        """Test creating a user profile successfully"""
        with app.app_context():
            # Create profile data
            profile_data = {
                'user_id': 'test_user_123',
                'email': 'test@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'company': 'Test Corp',
                'job_title': 'Developer'
            }
            
            # Create profile
            profile = UserProfile(**profile_data)
            db.session.add(profile)
            db.session.commit()
            
            # Verify profile was created
            saved_profile = UserProfile.query.filter_by(user_id='test_user_123').first()
            assert saved_profile is not None
            assert saved_profile.email == 'test@example.com'
            assert saved_profile.first_name == 'John'
            assert saved_profile.last_name == 'Doe'
            assert saved_profile.company == 'Test Corp'
            assert saved_profile.job_title == 'Developer'
            assert saved_profile.remaining_tokens == 5  # Default value
    
    def test_create_duplicate_profile_fails(self, app):
        """Test that creating duplicate profiles fails"""
        with app.app_context():
            # Create first profile
            profile1 = UserProfile(
                user_id='test_user_123',
                email='test@example.com',
                first_name='John',
                last_name='Doe',
                company='Test Corp',
                job_title='Developer'
            )
            db.session.add(profile1)
            db.session.commit()
            
            # Try to create duplicate profile
            profile2 = UserProfile(
                user_id='test_user_123',  # Same user_id
                email='test2@example.com',
                first_name='Jane',
                last_name='Smith',
                company='Other Corp',
                job_title='Manager'
            )
            db.session.add(profile2)
            
            # Should raise integrity error due to unique constraint
            with pytest.raises(Exception):
                db.session.commit()
    
    def test_get_user_profile_success(self, app):
        """Test retrieving user profile successfully"""
        with app.app_context():
            # Create profile
            profile = UserProfile(
                user_id='test_user_123',
                email='test@example.com',
                first_name='John',
                last_name='Doe',
                company='Test Corp',
                job_title='Developer'
            )
            db.session.add(profile)
            db.session.commit()
            
            # Retrieve profile
            retrieved_profile = UserProfile.query.filter_by(user_id='test_user_123').first()
            assert retrieved_profile is not None
            assert retrieved_profile.email == 'test@example.com'
            assert retrieved_profile.user_id == 'test_user_123'
    
    def test_get_nonexistent_profile(self, app):
        """Test retrieving non-existent profile returns None"""
        with app.app_context():
            profile = UserProfile.query.filter_by(user_id='nonexistent_user').first()
            assert profile is None


class TestUserScopedDataFiltering:
    """Test user-scoped data filtering logic"""
    
    # Use app fixture from conftest.py
    
    def test_document_owner_filtering(self, app):
        """Test filtering documents by owner_id"""
        with app.app_context():
            # Create documents for different users
            doc1 = Document(
                filename='doc1.txt',
                content='Content 1',
                owner_id='user_123'
            )
            doc2 = Document(
                filename='doc2.txt',
                content='Content 2',
                owner_id='user_456'
            )
            doc3 = Document(
                filename='doc3.txt',
                content='Content 3',
                owner_id='user_123'
            )
            
            db.session.add_all([doc1, doc2, doc3])
            db.session.commit()
            
            # Filter documents by owner
            user_123_docs = Document.query.filter_by(owner_id='user_123').all()
            user_456_docs = Document.query.filter_by(owner_id='user_456').all()
            
            assert len(user_123_docs) == 2
            assert len(user_456_docs) == 1
            
            # Verify correct documents returned
            user_123_filenames = [doc.filename for doc in user_123_docs]
            assert 'doc1.txt' in user_123_filenames
            assert 'doc3.txt' in user_123_filenames
            
            assert user_456_docs[0].filename == 'doc2.txt'
    
    def test_requirement_owner_filtering(self, app):
        """Test filtering requirements by owner_id"""
        with app.app_context():
            # Create requirements for different users
            req1 = Requirement(
                req_id='REQ-001',
                title='Requirement 1',
                owner_id='user_123'
            )
            req2 = Requirement(
                req_id='REQ-002',
                title='Requirement 2',
                owner_id='user_456'
            )
            req3 = Requirement(
                req_id='REQ-003',
                title='Requirement 3',
                owner_id='user_123'
            )
            
            db.session.add_all([req1, req2, req3])
            db.session.commit()
            
            # Filter requirements by owner
            user_123_reqs = Requirement.query.filter_by(owner_id='user_123').all()
            user_456_reqs = Requirement.query.filter_by(owner_id='user_456').all()
            
            assert len(user_123_reqs) == 2
            assert len(user_456_reqs) == 1
            
            # Verify correct requirements returned
            user_123_req_ids = [req.req_id for req in user_123_reqs]
            assert 'REQ-001' in user_123_req_ids
            assert 'REQ-003' in user_123_req_ids
            
            assert user_456_reqs[0].req_id == 'REQ-002'
    
    def test_project_summary_owner_filtering(self, app):
        """Test filtering project summaries by owner_id"""
        with app.app_context():
            # Create summaries for different users
            summary1 = ProjectSummary(
                content='Summary 1',
                owner_id='user_123'
            )
            summary2 = ProjectSummary(
                content='Summary 2',
                owner_id='user_456'
            )
            
            db.session.add_all([summary1, summary2])
            db.session.commit()
            
            # Filter summaries by owner
            user_123_summaries = ProjectSummary.query.filter_by(owner_id='user_123').all()
            user_456_summaries = ProjectSummary.query.filter_by(owner_id='user_456').all()
            
            assert len(user_123_summaries) == 1
            assert len(user_456_summaries) == 1
            
            assert user_123_summaries[0].content == 'Summary 1'
            assert user_456_summaries[0].content == 'Summary 2'
    
    def test_cross_user_data_isolation(self, app):
        """Test that users cannot access each other's data"""
        with app.app_context():
            # Create data for user_123
            doc = Document(
                filename='private_doc.txt',
                content='Private content',
                owner_id='user_123'
            )
            req = Requirement(
                req_id='REQ-PRIVATE',
                title='Private requirement',
                owner_id='user_123'
            )
            
            db.session.add_all([doc, req])
            db.session.commit()
            
            # Try to access as user_456
            user_456_docs = Document.query.filter_by(owner_id='user_456').all()
            user_456_reqs = Requirement.query.filter_by(owner_id='user_456').all()
            
            # Should not find any data
            assert len(user_456_docs) == 0
            assert len(user_456_reqs) == 0
            
            # Verify user_123 can access their own data
            user_123_docs = Document.query.filter_by(owner_id='user_123').all()
            user_123_reqs = Requirement.query.filter_by(owner_id='user_123').all()
            
            assert len(user_123_docs) == 1
            assert len(user_123_reqs) == 1


class TestSessionSecurity:
    """Test session security features"""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock SuperTokens session with security data"""
        session = Mock()
        session.get_user_id.return_value = "test_user_123"
        session.get_handle.return_value = "session_handle_123"
        session.get_access_token_payload.return_value = {
            'iat': 1640995200,  # Issued at time
            'exp': 1640998800,  # Expiration time
            'sub': 'test_user_123',
            'refreshedAt': 1640995200,
            'userAgent': 'Mozilla/5.0 Test Browser',
            'clientIP': '192.168.1.100'
        }
        return session
    
    def test_session_security_config_creation(self):
        """Test creating session security configuration"""
        config = SessionSecurityConfig()
        
        assert config.session_timeout > 0
        assert config.refresh_timeout > 0
        assert isinstance(config.csrf_protection, bool)
        assert config.same_site in ['strict', 'lax', 'none']
    
    @patch('app.session_security.time.time')
    def test_validate_session_timeout_valid(self, mock_time, mock_session):
        """Test session timeout validation with valid session"""
        # Mock current time (1 hour after session creation)
        mock_time.return_value = 1640998800
        
        result = validate_session_timeout(mock_session)
        assert result == True
    
    @patch('app.session_security.time.time')
    def test_validate_session_timeout_expired(self, mock_time, mock_session):
        """Test session timeout validation with expired session"""
        # Mock current time (8 hours after session creation - beyond max age)
        mock_time.return_value = 1641024000
        
        result = validate_session_timeout(mock_session)
        assert result == False
    
    @patch('app.session_security.time.time')
    def test_should_refresh_session_needed(self, mock_time, mock_session):
        """Test session refresh detection when refresh is needed"""
        # Mock current time (45 minutes after last refresh - beyond threshold)
        mock_time.return_value = 1640997900
        
        result = should_refresh_session(mock_session)
        assert result == True
    
    @patch('app.session_security.time.time')
    def test_should_refresh_session_not_needed(self, mock_time, mock_session):
        """Test session refresh detection when refresh is not needed"""
        # Mock current time (15 minutes after last refresh - within threshold)
        mock_time.return_value = 1640996100
        
        result = should_refresh_session(mock_session)
        assert result == False
    
    def test_validate_csrf_token_success(self, app):
        """Test CSRF token validation success"""
        with app.test_request_context(headers={'anti-csrf': 'valid_csrf_token'}):
            result = validate_csrf_token()
            assert result == True
    
    def test_get_security_headers(self):
        """Test security headers generation"""
        from app.session_security import get_security_headers
        
        headers = get_security_headers()
        
        assert 'X-Content-Type-Options' in headers
        assert 'X-Frame-Options' in headers
        assert 'X-XSS-Protection' in headers
        assert 'Referrer-Policy' in headers
        
        assert headers['X-Content-Type-Options'] == 'nosniff'
        assert headers['X-Frame-Options'] == 'DENY'
    
    @patch('app.session_security.validate_session_timeout')
    @patch('app.session_security.validate_csrf_token')
    def test_validate_session_integrity_success(self, mock_csrf, mock_timeout, mock_session, app):
        """Test comprehensive session integrity validation success"""
        mock_timeout.return_value = True
        mock_csrf.return_value = True
        
        with app.test_request_context(
            headers={'User-Agent': 'Mozilla/5.0 Test Browser'},
            environ_base={'REMOTE_ADDR': '192.168.1.100'}
        ):
            result = security_validate_session_integrity(mock_session)
            
            assert result['valid'] == True
            assert len(result['errors']) == 0


class TestErrorHandling:
    """Test error handling for authentication components"""
    
    def test_create_session_error_response_unauthorized(self):
        """Test creating error response for unauthorized error"""
        from supertokens_python.recipe.session.exceptions import UnauthorisedError
        
        error = UnauthorisedError("Session expired")
        response, status_code = create_session_error_response(error)
        
        assert status_code == 401
        assert response['error'] == 'unauthorized'
        assert 'message' in response
    
    def test_create_session_error_response_forbidden(self):
        """Test creating error response for forbidden error"""
        from supertokens_python.recipe.session.exceptions import InvalidClaimsError
        
        error = InvalidClaimsError("Invalid claims", [])
        response, status_code = create_session_error_response(error)
        
        assert status_code == 403
        assert response['error'] == 'forbidden'
        assert 'message' in response
    
    def test_create_session_error_response_token_theft(self):
        """Test creating error response for token theft error"""
        from supertokens_python.recipe.session.exceptions import TokenTheftError
        
        error = TokenTheftError("Token theft detected", "session_handle", "user_id")
        response, status_code = create_session_error_response(error)
        
        assert status_code == 401
        assert response['error'] == 'token_theft'
        assert 'message' in response
    
    def test_create_session_error_response_session_error(self):
        """Test creating error response for session error"""
        error = SessionError("Custom session error")
        response, status_code = create_session_error_response(error)
        
        assert status_code == 401
        assert response['error'] == 'session_error'
        assert response['message'] == 'Custom session error'
    
    def test_create_session_error_response_permission_error(self):
        """Test creating error response for permission error"""
        error = PermissionError("Missing permissions")
        response, status_code = create_session_error_response(error)
        
        assert status_code == 403
        assert response['error'] == 'permission_error'
        assert response['message'] == 'Missing permissions'
    
    def test_create_session_error_response_generic_error(self):
        """Test creating error response for generic error"""
        error = Exception("Unexpected error")
        response, status_code = create_session_error_response(error)
        
        assert status_code == 500
        assert response['error'] == 'internal_error'
        assert 'message' in response