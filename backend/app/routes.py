import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pypdf
import docx
import json

from .main import db
from .models import Document
from .rag_service import process_and_store_document

api_bp = Blueprint('api', __name__, url_prefix='/api')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'md', 'json'}

@api_bp.route('/')
def index():
    return jsonify({"message": "Welcome to the Clarity AI API!"})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_file_content(file_storage):
    filename = file_storage.filename
    extension = filename.rsplit('.', 1)[1].lower()
    content = ""
    file_storage.seek(0)
    
    if extension in ['txt', 'md']:
        content = file_storage.read().decode('utf-8')
    elif extension == 'json':
        try:
            json_data = json.load(file_storage)
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
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        new_document = None
        
        try:
            content = parse_file_content(file)
            
            new_document = Document(filename=filename, content=content)
            db.session.add(new_document)
            db.session.commit()
            
            # This is now a separate step with its own error handling
            process_and_store_document(new_document)
            
            return jsonify({"message": "File uploaded and processed successfully", "id": new_document.id}), 201
            
        except Exception as e:
            # --- IMPROVED ERROR LOGGING ---
            # This will now print the exact error to your backend console
            print(f"An error occurred during file processing: {str(e)}")
            db.session.rollback()
            return jsonify({"error": f"Failed to process file: {str(e)}"}), 500
            
    return jsonify({"error": "File type not allowed"}), 400

