import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pypdf
import docx
import json

from .main import db
from .models import Document

api_bp = Blueprint('api', __name__, url_prefix='/api')

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'md', 'json'}

@api_bp.route('/')
def index():
    """A simple health-check or index route for the API."""
    return jsonify({"message": "Welcome to the Clarity AI API!"})


def allowed_file(filename):
    """Checks if a file's extension is in the ALLOWED_EXTENSIONS set."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_file_content(file_storage):
    """Parses the content of a FileStorage object based on its extension."""
    filename = file_storage.filename
    extension = filename.rsplit('.', 1)[1].lower()
    
    content = ""
    file_storage.seek(0) # Reset file pointer to the beginning
    
    if extension in ['txt', 'md']:
        content = file_storage.read().decode('utf-8')
    elif extension == 'json':
        try:
            json_data = json.load(file_storage)
            # Convert JSON to a pretty-printed string for storage
            content = json.dumps(json_data, indent=2)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON file.")
    elif extension == 'pdf':
        pdf_reader = pypdf.PdfReader(file_storage)
        for page in pdf_reader.pages:
            content += page.extract_text()
    elif extension == 'docx':
        doc = docx.Document(file_storage)
        for para in doc.paragraphs:
            content += para.text + '\n'
            
    return content

@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handles file uploads, parses content, and saves to the database."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        try:
            content = parse_file_content(file)
            
            # Create a new Document record and save it to the DB
            new_document = Document(filename=filename, content=content)
            db.session.add(new_document)
            db.session.commit()
            
            return jsonify({"message": "File uploaded and processed successfully", "id": new_document.id}), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to process file: {str(e)}"}), 500
            
    return jsonify({"error": "File type not allowed"}), 400
