import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pypdf
import docx
import json

from .main import db
from .models import Document, Requirement, Tag, ProjectSummary
from .rag_service import (
    process_and_store_document,
    generate_project_requirements,
    generate_project_summary,
    delete_document_from_rag
)

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

# --- NEW: Get all documents ---
@api_bp.route('/documents', methods=['GET'])
def get_documents():
    """
    Fetches all documents from the database.
    """
    try:
        documents = Document.query.order_by(Document.created_at.desc()).all()
        results = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in documents
        ]
        return jsonify(results)
    except Exception as e:
        print(f"An error occurred while fetching documents: {str(e)}")
        return jsonify({"error": "Failed to fetch documents"}), 500

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
            
            process_and_store_document(new_document)
            
            # Return the new document object, matching the /documents GET route
            return jsonify({
                "message": "File uploaded and processed successfully",
                "document": {
                    "id": new_document.id,
                    "filename": new_document.filename,
                    "created_at": new_document.created_at.isoformat() if new_document.created_at else None
                }
            }), 201
            
        except Exception as e:
            print(f"An error occurred during file processing: {str(e)}")
            db.session.rollback()
            return jsonify({"error": f"Failed to process file: {str(e)}"}), 500
            
    return jsonify({"error": "File type not allowed"}), 400

# --- NEW: Delete a document ---
@api_bp.route('/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """
    Deletes a document from the database and the RAG vector store.
    """
    try:
        document = Document.query.get(document_id)
        if not document:
            return jsonify({"error": "Document not found"}), 404

        # --- THIS IS THE FIX ---
        # 1. Delete from RAG first.
        delete_document_from_rag(document_id)
        
        # 2. Delete the document object from the session.
        # SQLAlchemy will automatically handle deleting associated requirements
        # (due to `cascade="all, delete-orphan"` in models.py) and
        # the entries in the `requirement_tags` table (due to the `secondary`
        # relationship config) in the correct order.
        db.session.delete(document)
        
        # 3. Commit the transaction
        db.session.commit()
        # ---------------------
        
        return jsonify({"message": f"Document ID {document_id} and associated data deleted."}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"An error occurred during document deletion: {str(e)}")
        return jsonify({"error": f"Failed to delete document: {str(e)}"}), 500

# --- REMOVED: /analyze ---
# This endpoint is no longer needed as the query is not user-driven.

# --- NEW: Trigger for requirements generation ---
@api_bp.route('/requirements/generate', methods=['POST'])
def trigger_requirements_generation():
    """
    Triggers a full regeneration of all requirements from all documents.
    This clears all existing requirements first.
    """
    try:
        total_generated = generate_project_requirements()
        return jsonify({
            "message": f"Successfully generated {total_generated} new requirements."
        })
    except Exception as e:
        print(f"An error occurred during requirements generation: {str(e)}")
        return jsonify({"error": f"Failed to generate requirements: {str(e)}"}), 500

@api_bp.route('/requirements', methods=['GET'])
def get_requirements():
    """
    Fetches all requirements from the database, including their associated
    tags and the filename of their source document.
    """
    try:
        requirements = Requirement.query.options(
            db.joinedload(Requirement.tags),
            db.joinedload(Requirement.source_document)
        ).all()

        results = []
        for req in requirements:
            results.append({
                "id": req.id,
                "req_id": req.req_id,
                "title": req.title,
                "description": req.description,
                "status": req.status,
                "priority": req.priority,
                "source_document_filename": req.source_document.filename if req.source_document else None,
                "tags": [{"id": tag.id, "name": tag.name} for tag in req.tags]
            })
            
        return jsonify(results)

    except Exception as e:
        print(f"An error occurred while fetching requirements: {str(e)}")
        return jsonify({"error": "Failed to fetch requirements"}), 500

# --- NEW: Get requirements count ---
@api_bp.route('/requirements/count', methods=['GET'])
def get_requirements_count():
    """
    Fetches a simple count of all requirements.
    """
    try:
        count = db.session.query(Requirement.id).count()
        return jsonify({"count": count})
    except Exception as e:
        print(f"An error occurred while fetching requirements count: {str(e)}")
        return jsonify({"error": "Failed to fetch requirements count"}), 500

# --- NEW: Get project summary ---
@api_bp.route('/summary', methods=['GET'])
def get_summary():
    """
    Fetches the latest generated project summary from the database.
    """
    try:
        # Get the most recent summary
        latest_summary = ProjectSummary.query.order_by(ProjectSummary.created_at.desc()).first()
        
        if latest_summary:
            return jsonify({
                "summary": latest_summary.content,
                "created_at": latest_summary.created_at.isoformat() if latest_summary.created_at else None
            })
        else:
            return jsonify({
                "summary": "No summary has been generated yet. Upload documents and click 'Regenerate Summary' on the Overview page.",
                "created_at": None
            })
    except Exception as e:
        print(f"An error occurred while fetching summary: {str(e)}")
        return jsonify({"error": "Failed to fetch summary"}), 500

# --- NEW: Trigger for summary generation ---
@api_bp.route('/summary/generate', methods=['POST'])
def trigger_summary_generation():
    """
    Triggers generation of a new project-wide summary.
    This retrieves context from ALL documents.
    """
    try:
        # Call the new summary generation function
        summary_output = generate_project_summary()
        
        # Save the new summary to the database
        new_summary = ProjectSummary(content=summary_output)
        db.session.add(new_summary)
        db.session.commit()
        
        return jsonify({
            "message": "Summary generated successfully.",
            "summary": new_summary.content,
            "created_at": new_summary.created_at.isoformat() if new_summary.created_at else None
        })
    except Exception as e:
        db.session.rollback()
        print(f"An error occurred during summarization: {str(e)}")
        return jsonify({"error": f"Failed to summarize project: {str(e)}"}), 500