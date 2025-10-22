from app.main import create_app, db
from app.models import Document, Requirement, Tag

class TestDashboardAPI:
    def test_get_requirements(self):
        """
        GIVEN a database with a document, tags, and a requirement linked to them
        WHEN a GET request is made to /api/requirements
        THEN the response should contain a list of requirements with their tags and source document
        """
        app = create_app()
        app.config.update({"TESTING": True})
        client = app.test_client()

        # Setup: Create mock data in the database
        with app.app_context():
            # Clear existing data to ensure a clean test
            db.session.query(Requirement).delete()
            db.session.query(Tag).delete()
            db.session.query(Document).delete()
            db.session.commit()

            # Create new mock data
            doc = Document(filename="test_spec.pdf", content="Some content")
            tag1 = Tag(name="Security")
            tag2 = Tag(name="Core Feature")
            
            req = Requirement(
                req_id="REQ-TEST-001",
                title="Test user story",
                status="Draft",
                priority="High",
                source_document=doc
            )
            req.tags.append(tag1)
            req.tags.append(tag2)

            db.session.add_all([doc, tag1, tag2, req])
            db.session.commit()

        # Action: Make the GET request to the new endpoint
        response = client.get('/api/requirements')

        # Assertion: Check the response
        assert response.status_code == 200
        data = response.json
        assert isinstance(data, list)
        assert len(data) == 1
        
        requirement_data = data[0]
        assert requirement_data['req_id'] == "REQ-TEST-001"
        assert requirement_data['title'] == "Test user story"
        assert requirement_data['source_document_filename'] == "test_spec.pdf"
        
        assert 'tags' in requirement_data
        assert isinstance(requirement_data['tags'], list)
        assert len(requirement_data['tags']) == 2
        
        tag_names = {tag['name'] for tag in requirement_data['tags']}
        assert "Security" in tag_names
        assert "Core Feature" in tag_names