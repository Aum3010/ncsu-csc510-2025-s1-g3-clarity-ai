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
from app.main import create_app


class TestFlaskAuthenticationIntegration:
    """Integration tests for Flask authentication with SuperTokens"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app with database"""
        app = create_app()
        app.config.update({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False
        })
        yield app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint works"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'Clarity AI API'
        assert 'timestamp' in data
    
    def test_unauthenticated_access_denied(self, client):
        """Test that unauthenticated requests are denied access to protected routes"""
        
        # Test all protected endpoints without authentication
        protected_endpoints = [
            '/api/documents',
            '/api/requirements',
            '/api/requirements/count',
            '/api/summary'
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            
            # Should return 401 for unauthenticated access
            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data
    
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
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_complete_admin_authentication_flow(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_admin):
        """Test complete authentication flow for admin user accessing protected resources"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_admin, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_admin
        mock_get_roles.side_effect = self.setup_mock_user_roles("admin_user_123", ["admin"])
        
        with app.app_context():
            from app.main import db
            from app.models import Document
            
            # Create test data
            doc = Document(filename="test.txt", content="Test content", owner_id="admin_user_123")
            db.session.add(doc)
            db.session.commit()
            
            # Test accessing protected document endpoint
            response = client.get('/api/documents')
            
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]['filename'] == "test.txt"
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_complete_core_user_authentication_flow(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_core_user):
        """Test complete authentication flow for core user with appropriate permissions"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_core_user, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_core_user
        mock_get_roles.side_effect = self.setup_mock_user_roles("core_user_456", ["core-user"])
        
        with app.app_context():
            # Create test data for core user
            req = Requirement(
                req_id="REQ-001",
                title="Test Requirement",
                owner_id="core_user_456"
            )
            db.session.add(req)
            db.session.commit()
            
            # Test accessing requirements endpoint
            response = client.get('/api/requirements')
            
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]['req_id'] == "REQ-001"
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_pilot_user_limited_access_flow(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_pilot_user):
        """Test that pilot user has limited access to only basic features"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_pilot_user, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_pilot_user
        mock_get_roles.side_effect = self.setup_mock_user_roles("pilot_user_789", ["pilot-user"])
        
        with app.app_context():
            # Create test document for pilot user
            doc = Document(filename="pilot_doc.txt", content="Pilot content", owner_id="pilot_user_789")
            db.session.add(doc)
            db.session.commit()
            
            # Test accessing documents (should work)
            response = client.get('/api/documents')
            assert response.status_code == 200
            
            # Test accessing requirements (should fail - pilot users don't have requirements:read)
            response = client.get('/api/requirements')
            assert response.status_code == 403
            
            # Test accessing summary (should fail - pilot users don't have summary:read)
            response = client.get('/api/summary')
            assert response.status_code == 403
    
    def test_unauthenticated_access_denied(self, client):
        """Test that unauthenticated requests are denied access to protected routes"""
        
        # Test all protected endpoints without authentication
        protected_endpoints = [
            '/api/documents',
            '/api/upload',
            '/api/requirements',
            '/api/requirements/generate',
            '/api/requirements/count',
            '/api/summary',
            '/api/summary/generate'
        ]
        
        for endpoint in protected_endpoints:
            if endpoint in ['/api/upload', '/api/requirements/generate', '/api/summary/generate']:
                response = client.post(endpoint)
            else:
                response = client.get(endpoint)
            
            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data
            assert data['error'] in ['unauthorized', 'authentication_error']


class TestRoleBasedAccessControl(TestFlaskAuthenticationIntegration):
    """Test role-based access control across all protected routes"""
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_admin_access_to_all_routes(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_admin):
        """Test that admin users can access all protected routes"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_admin, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_admin
        mock_get_roles.side_effect = self.setup_mock_user_roles("admin_user_123", ["admin"])
        
        with app.app_context():
            # Create test data
            doc = Document(filename="admin_test.txt", content="Admin content", owner_id="admin_user_123")
            req = Requirement(req_id="REQ-ADMIN", title="Admin Requirement", owner_id="admin_user_123")
            summary = ProjectSummary(content="Admin Summary", owner_id="admin_user_123")
            db.session.add_all([doc, req, summary])
            db.session.commit()
            
            # Test all GET endpoints
            get_endpoints = [
                '/api/documents',
                '/api/requirements',
                '/api/requirements/count',
                '/api/summary'
            ]
            
            for endpoint in get_endpoints:
                response = client.get(endpoint)
                assert response.status_code == 200, f"Admin should access {endpoint}"
            
            # Test POST endpoints (with mock data)
            with patch('app.rag_service.generate_project_requirements') as mock_gen_req:
                mock_gen_req.return_value = 5
                response = client.post('/api/requirements/generate')
                assert response.status_code == 200
            
            with patch('app.rag_service.generate_project_summary') as mock_gen_summary:
                mock_gen_summary.return_value = "Generated summary"
                response = client.post('/api/summary/generate')
                assert response.status_code == 200
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_core_user_permissions_enforcement(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_core_user):
        """Test that core users have appropriate permissions enforced"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_core_user, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_core_user
        mock_get_roles.side_effect = self.setup_mock_user_roles("core_user_456", ["core-user"])
        
        with app.app_context():
            # Create test data for core user
            doc = Document(filename="core_test.txt", content="Core content", owner_id="core_user_456")
            req = Requirement(req_id="REQ-CORE", title="Core Requirement", owner_id="core_user_456")
            summary = ProjectSummary(content="Core Summary", owner_id="core_user_456")
            db.session.add_all([doc, req, summary])
            db.session.commit()
            
            # Test endpoints core users should access
            allowed_endpoints = [
                '/api/documents',
                '/api/requirements',
                '/api/requirements/count',
                '/api/summary'
            ]
            
            for endpoint in allowed_endpoints:
                response = client.get(endpoint)
                assert response.status_code == 200, f"Core user should access {endpoint}"
            
            # Test write operations core users should be able to perform
            with patch('app.rag_service.generate_project_requirements') as mock_gen_req:
                mock_gen_req.return_value = 3
                response = client.post('/api/requirements/generate')
                assert response.status_code == 200
            
            with patch('app.rag_service.generate_project_summary') as mock_gen_summary:
                mock_gen_summary.return_value = "Core generated summary"
                response = client.post('/api/summary/generate')
                assert response.status_code == 200
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_pilot_user_restricted_access(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_pilot_user):
        """Test that pilot users have restricted access to only basic features"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_pilot_user, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_pilot_user
        mock_get_roles.side_effect = self.setup_mock_user_roles("pilot_user_789", ["pilot-user"])
        
        with app.app_context():
            # Create test data for pilot user
            doc = Document(filename="pilot_test.txt", content="Pilot content", owner_id="pilot_user_789")
            db.session.add(doc)
            db.session.commit()
            
            # Test endpoints pilot users should access
            response = client.get('/api/documents')
            assert response.status_code == 200
            
            # Test endpoints pilot users should NOT access
            restricted_endpoints = [
                '/api/requirements',
                '/api/requirements/count',
                '/api/summary'
            ]
            
            for endpoint in restricted_endpoints:
                response = client.get(endpoint)
                assert response.status_code == 403, f"Pilot user should not access {endpoint}"
            
            # Test write operations pilot users should NOT perform
            restricted_post_endpoints = [
                '/api/requirements/generate',
                '/api/summary/generate'
            ]
            
            for endpoint in restricted_post_endpoints:
                response = client.post(endpoint)
                assert response.status_code == 403, f"Pilot user should not access {endpoint}"
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_cross_user_data_isolation(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_core_user):
        """Test that users can only access their own data"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_core_user, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_core_user
        mock_get_roles.side_effect = self.setup_mock_user_roles("core_user_456", ["core-user"])
        
        with app.app_context():
            # Create data for different users
            doc_user1 = Document(filename="user1_doc.txt", content="User 1 content", owner_id="core_user_456")
            doc_user2 = Document(filename="user2_doc.txt", content="User 2 content", owner_id="other_user_999")
            
            req_user1 = Requirement(req_id="REQ-USER1", title="User 1 Req", owner_id="core_user_456")
            req_user2 = Requirement(req_id="REQ-USER2", title="User 2 Req", owner_id="other_user_999")
            
            summary_user1 = ProjectSummary(content="User 1 Summary", owner_id="core_user_456")
            summary_user2 = ProjectSummary(content="User 2 Summary", owner_id="other_user_999")
            
            db.session.add_all([doc_user1, doc_user2, req_user1, req_user2, summary_user1, summary_user2])
            db.session.commit()
            
            # Test documents endpoint - should only return user's own documents
            response = client.get('/api/documents')
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 1
            assert data[0]['filename'] == "user1_doc.txt"
            
            # Test requirements endpoint - should only return user's own requirements
            response = client.get('/api/requirements')
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 1
            assert data[0]['req_id'] == "REQ-USER1"
            
            # Test summary endpoint - should only return user's own summary
            response = client.get('/api/summary')
            assert response.status_code == 200
            data = response.get_json()
            assert data['summary'] == "User 1 Summary"
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_document_deletion_with_access_control(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_core_user):
        """Test document deletion with proper access control"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_core_user, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session_core_user
        mock_get_roles.side_effect = self.setup_mock_user_roles("core_user_456", ["core-user"])
        
        with app.app_context():
            # Create documents for different users
            doc_owned = Document(filename="owned_doc.txt", content="Owned content", owner_id="core_user_456")
            doc_other = Document(filename="other_doc.txt", content="Other content", owner_id="other_user_999")
            db.session.add_all([doc_owned, doc_other])
            db.session.commit()
            
            owned_doc_id = doc_owned.id
            other_doc_id = doc_other.id
            
            # Mock the RAG service delete function
            with patch('app.rag_service.delete_document_from_rag') as mock_delete_rag:
                # Test deleting own document (should succeed)
                response = client.delete(f'/api/documents/{owned_doc_id}')
                assert response.status_code == 200
                mock_delete_rag.assert_called_once_with(owned_doc_id)
                
                # Verify document was deleted
                deleted_doc = Document.query.get(owned_doc_id)
                assert deleted_doc is None
                
                # Test deleting other user's document (should fail)
                response = client.delete(f'/api/documents/{other_doc_id}')
                assert response.status_code == 404  # Not found due to owner_id filter
                
                # Verify other user's document still exists
                other_doc_still_exists = Document.query.get(other_doc_id)
                assert other_doc_still_exists is not None


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
    
    @patch('supertokens_python.recipe.userroles.add_role_to_user')
    def test_default_role_assignment(self, mock_add_role, client, app):
        """Test that new users are assigned default roles"""
        
        with app.app_context():
            # Mock successful role assignment
            mock_add_role.return_value = AsyncMock()
            
            profile_data = {
                'user_id': 'role_test_user',
                'email': 'roletest@example.com',
                'first_name': 'Role',
                'last_name': 'Test',
                'company': 'Role Company',
                'job_title': 'Role Job'
            }
            
            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_until_complete.return_value = Mock()
                mock_get_loop.return_value = mock_loop
                
                response = client.post('/api/auth/profile',
                                     data=json.dumps(profile_data),
                                     content_type='application/json')
                
                assert response.status_code == 201
                data = response.get_json()
                assert data['profile']['assigned_role'] == 'pilot-user'


class TestSessionSecurityIntegration(TestFlaskAuthenticationIntegration):
    """Test session security features in integration scenarios"""
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    def test_session_integrity_validation_failure(self, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_core_user):
        """Test that requests with invalid session integrity are rejected"""
        
        # Setup mocks - session integrity fails
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_core_user, *args, **kwargs)
        mock_validate.return_value = {
            'valid': False,
            'errors': ['Session has exceeded timeout limits'],
            'warnings': []
        }
        mock_get_roles.side_effect = self.setup_mock_user_roles("core_user_456", ["core-user"])
        
        with app.app_context():
            response = client.get('/api/documents')
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['error'] == 'session_invalid'
            assert 'Session integrity validation failed' in data['message']
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_session_refresh_during_request(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app, mock_session_core_user):
        """Test that sessions are refreshed when needed during requests"""
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session_core_user, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': ['Session should be refreshed']}
        
        # Mock refresh to return updated session
        refreshed_session = Mock()
        refreshed_session.get_user_id.return_value = "core_user_456"
        refreshed_session.get_handle.return_value = "refreshed_handle"
        refreshed_session.get_access_token_payload.return_value = {
            'iat': 1640995200,
            'exp': 1640998800,
            'sub': 'core_user_456',
            'refreshedAt': 1640998000  # Updated refresh time
        }
        mock_refresh.return_value = refreshed_session
        mock_get_roles.side_effect = self.setup_mock_user_roles("core_user_456", ["core-user"])
        
        with app.app_context():
            response = client.get('/api/documents')
            
            assert response.status_code == 200
            mock_refresh.assert_called_once()
    
    @patch('app.auth_service.verify_session')
    def test_supertokens_exception_handling(self, mock_verify, client, app):
        """Test handling of SuperTokens-specific exceptions"""
        
        from supertokens_python.recipe.session.exceptions import UnauthorisedError
        
        # Mock verify_session to raise UnauthorisedError
        def mock_decorator(f):
            def wrapper(*args, **kwargs):
                raise UnauthorisedError("Session expired")
            return wrapper
        
        mock_verify.return_value = mock_decorator
        
        with app.app_context():
            response = client.get('/api/documents')
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['error'] == 'unauthorized'


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
    
    @patch('supertokens_python.recipe.userroles.get_all_roles')
    def test_supertokens_health_check_success(self, mock_get_all_roles, client, app):
        """Test SuperTokens health check when service is healthy"""
        
        # Mock successful SuperTokens response
        mock_response = Mock()
        mock_response.roles = ['admin', 'core-user', 'pilot-user']
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.run_until_complete.return_value = mock_response
            mock_get_loop.return_value = mock_loop
            
            with app.app_context():
                response = client.get('/api/health/supertokens')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['status'] == 'healthy'
                assert data['service'] == 'SuperTokens'
                assert data['roles_configured'] == 3
    
    @patch('supertokens_python.recipe.userroles.get_all_roles')
    def test_supertokens_health_check_failure(self, mock_get_all_roles, client, app):
        """Test SuperTokens health check when service is unhealthy"""
        
        # Mock SuperTokens connection failure
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.run_until_complete.side_effect = Exception("Connection failed")
            mock_get_loop.return_value = mock_loop
            
            with app.app_context():
                response = client.get('/api/health/supertokens')
                
                assert response.status_code == 503
                data = response.get_json()
                assert data['status'] == 'unhealthy'
                assert 'SuperTokens connectivity error' in data['message']
    
    def test_database_health_check_success(self, client, app):
        """Test database health check when database is healthy"""
        
        with app.app_context():
            response = client.get('/api/health/database')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'Database'
            assert 'Database connection is working' in data['message']
    
    @patch('app.main.db.session.execute')
    def test_database_health_check_failure(self, mock_execute, client, app):
        """Test database health check when database is unhealthy"""
        
        # Mock database connection failure
        mock_execute.side_effect = Exception("Database connection failed")
        
        with app.app_context():
            response = client.get('/api/health/database')
            
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'unhealthy'
            assert 'Database connectivity error' in data['message']
    
    @patch('supertokens_python.recipe.userroles.get_all_roles')
    def test_full_health_check_all_healthy(self, mock_get_all_roles, client, app):
        """Test full health check when all services are healthy"""
        
        # Mock successful SuperTokens response
        mock_response = Mock()
        mock_response.roles = ['admin', 'core-user', 'pilot-user']
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.run_until_complete.return_value = mock_response
            mock_get_loop.return_value = mock_loop
            
            with app.app_context():
                response = client.get('/api/health/full')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['overall_status'] == 'healthy'
                assert data['services']['api']['status'] == 'healthy'
                assert data['services']['database']['status'] == 'healthy'
                assert data['services']['supertokens']['status'] == 'healthy'

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
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_admin_user_access(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app):
        """Test that admin users can access protected endpoints"""
        
        # Create mock session for admin user
        mock_session = self.create_mock_session("admin_user_123", ["admin"])
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session
        mock_get_roles.side_effect = self.setup_mock_user_roles("admin_user_123", ["admin"])
        
        # Test accessing protected endpoints
        response = client.get('/api/documents')
        assert response.status_code == 200
        
        response = client.get('/api/requirements')
        assert response.status_code == 200
        
        response = client.get('/api/summary')
        assert response.status_code == 200
    
    @patch('app.auth_service.verify_session')
    @patch('supertokens_python.recipe.userroles.get_roles_for_user')
    @patch('app.session_security.validate_session_integrity')
    @patch('app.session_security.refresh_session_if_needed')
    def test_pilot_user_restricted_access(self, mock_refresh, mock_validate, mock_get_roles, mock_verify, client, app):
        """Test that pilot users have restricted access"""
        
        # Create mock session for pilot user
        mock_session = self.create_mock_session("pilot_user_789", ["pilot-user"])
        
        # Setup mocks
        mock_verify.return_value = lambda f: lambda *args, **kwargs: f(mock_session, *args, **kwargs)
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
        mock_refresh.return_value = mock_session
        mock_get_roles.side_effect = self.setup_mock_user_roles("pilot_user_789", ["pilot-user"])
        
        # Test accessing documents (should work)
        response = client.get('/api/documents')
        assert response.status_code == 200
        
        # Test accessing requirements (should fail - pilot users don't have requirements:read)
        response = client.get('/api/requirements')
        assert response.status_code == 403
        
        # Test accessing summary (should fail - pilot users don't have summary:read)
        response = client.get('/api/summary')
        assert response.status_code == 403
    
    def test_session_security_configuration(self):
        """Test session security configuration"""
        from app.session_security import SessionSecurityConfig
        
        config = SessionSecurityConfig()
        
        # Verify default values are reasonable
        assert config.session_timeout > 0
        assert config.refresh_timeout > config.session_timeout
        assert config.max_session_age > config.refresh_timeout
        assert config.session_refresh_threshold > 0
        assert config.same_site in ['strict', 'lax', 'none']
        
        # Test cookie security detection
        secure_setting = config.get_cookie_secure_setting()
        assert isinstance(secure_setting, bool)
        
        # Test CSRF setting
        csrf_setting = config.get_csrf_setting()
        assert csrf_setting in ['NONE', 'VIA_TOKEN', 'VIA_CUSTOM_HEADER']
    
    def test_session_timeout_validation(self):
        """Test session timeout validation logic"""
        from app.session_security import validate_session_timeout
        
        # Create mock session with known timestamps
        mock_session = Mock()
        
        # Test valid session (created 30 minutes ago)
        import time
        current_time = int(time.time())
        session_created = current_time - 1800  # 30 minutes ago
        
        mock_session.get_access_token_payload.return_value = {
            'iat': session_created,
            'refreshedAt': session_created
        }
        
        with patch('app.session_security.time.time', return_value=current_time):
            result = validate_session_timeout(mock_session)
            assert result == True
        
        # Test expired session (created 8 hours ago)
        old_session_created = current_time - 28800  # 8 hours ago
        mock_session.get_access_token_payload.return_value = {
            'iat': old_session_created,
            'refreshedAt': old_session_created
        }
        
        with patch('app.session_security.time.time', return_value=current_time):
            result = validate_session_timeout(mock_session)
            assert result == False


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
    
    @patch('app.auth_service.verify_session')
    def test_supertokens_exception_handling(self, mock_verify, client, app):
        """Test handling of SuperTokens-specific exceptions"""
        
        from supertokens_python.recipe.session.exceptions import UnauthorisedError
        
        # Mock verify_session to raise UnauthorisedError
        def mock_decorator(f):
            def wrapper(*args, **kwargs):
                raise UnauthorisedError("Session expired")
            return wrapper
        
        mock_verify.return_value = mock_decorator
        
        response = client.get('/api/documents')
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'unauthorized'


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
    
    @patch('supertokens_python.recipe.userroles.get_all_roles')
    def test_supertokens_health_check_success(self, mock_get_all_roles, client, app):
        """Test SuperTokens health check when service is healthy"""
        
        # Mock successful SuperTokens response
        mock_response = Mock()
        mock_response.roles = ['admin', 'core-user', 'pilot-user']
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.run_until_complete.return_value = mock_response
            mock_get_loop.return_value = mock_loop
            
            response = client.get('/api/health/supertokens')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'SuperTokens'
            assert data['roles_configured'] == 3
    
    @patch('supertokens_python.recipe.userroles.get_all_roles')
    def test_supertokens_health_check_failure(self, mock_get_all_roles, client, app):
        """Test SuperTokens health check when service is unhealthy"""
        
        # Mock SuperTokens connection failure
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.run_until_complete.side_effect = Exception("Connection failed")
            mock_get_loop.return_value = mock_loop
            
            response = client.get('/api/health/supertokens')
            
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'unhealthy'
            assert 'SuperTokens connectivity error' in data['message']