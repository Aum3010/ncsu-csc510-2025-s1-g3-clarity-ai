from .main import db
from datetime import datetime

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    requirements = db.relationship('Requirement', back_populates='source_document')

class Requirement(db.Model):
    __tablename__ = 'requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    req_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Draft')
    priority = db.Column(db.String(50), default='Medium')
    
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    source_document = db.relationship('Document', back_populates='requirements')

    def __repr__(self):
        return f"<Requirement {self.req_id}: {self.title}>"
