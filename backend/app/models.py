from .main import db  # Import the 'db' object from our main file
from datetime import datetime

# We'll start with two main tables:
# 1. Document: To track the files we upload
# 2. Requirement: To store the structured data from the LLM

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False) # The full, parsed text
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # This creates a "one-to-many" relationship:
    # One Document can have many Requirements
    requirements = db.relationship('Requirement', back_populates='source_document')

class Requirement(db.Model):
    __tablename__ = 'requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    req_id = db.Column(db.String(50), unique=True, nullable=False) # e.g., "REQ-001"
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Draft')
    priority = db.Column(db.String(50), default='Medium')
    
    # This is the "many-to-one" side of the relationship
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    source_document = db.relationship('Document', back_populates='requirements')

    def __repr__(self):
        return f"<Requirement {self.req_id}: {self.title}>"