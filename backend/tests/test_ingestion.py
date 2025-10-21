import io
from app.main import create_app, db
from app.models import Document

# We will group our ingestion tests in a class
class TestIngestion:

    def test_upload_txt_file(self):
        """
        GIVEN a Flask application configured for testing
        WHEN a POST request is made to /api/upload with a .txt file
        THEN a new Document should be created in the database
        """
        app = create_app()
        app.config.update({
            "TESTING": True,
        })
        client = app.test_client()

        # Create a mock .txt file in memory
        file_content = b"This is a test text file."
        file_data = {
            'file': (io.BytesIO(file_content), 'test.txt')
        }

        # Make the POST request
        response = client.post('/api/upload', content_type='multipart/form-data', data=file_data)

        # Assert the response is correct
        assert response.status_code == 201
        assert "id" in response.json
        new_doc_id = response.json["id"]

        # Assert the document was saved to the database
        with app.app_context():
            doc = db.session.get(Document, new_doc_id)
            assert doc is not None
            assert doc.filename == 'test.txt'
            assert doc.content == file_content.decode('utf-8')