from .main import db
from datetime import datetime

requirement_tags = db.Table('requirement_tags',
    db.Column('requirement_id', db.Integer, db.ForeignKey('requirements.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.String(255), nullable=True)  # SuperTokens user ID
    requirements = db.relationship('Requirement', back_populates='source_document', cascade="all, delete-orphan")

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#cccccc')

    def __repr__(self):
        return f"<Tag {self.name}>"

class Requirement(db.Model):
    __tablename__ = 'requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    req_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='Draft')
    priority = db.Column(db.String(50), default='Medium')
    owner_id = db.Column(db.String(255), nullable=True)  # SuperTokens user ID
    
    # Renamed document_id to source_document_id for clarity
    source_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    source_document = db.relationship('Document', back_populates='requirements')

    # It links a Requirement to the Tag model through our association table.
    tags = db.relationship('Tag', secondary=requirement_tags, lazy='subquery',
        backref=db.backref('requirements', lazy=True))

    def __repr__(self):
        return f"<Requirement {self.req_id}: {self.title}>"

class ProjectSummary(db.Model):
    __tablename__ = 'project_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.String(255), nullable=True)  # SuperTokens user ID

    def __repr__(self):
        return f"<ProjectSummary {self.id} created at {self.created_at}>"

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), unique=True, nullable=False)  # SuperTokens user ID
    email = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    job_title = db.Column(db.String(255), nullable=False)
    remaining_tokens = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserProfile {self.email}>"
