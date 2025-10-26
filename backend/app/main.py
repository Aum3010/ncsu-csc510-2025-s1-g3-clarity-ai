import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

# --- Database Setup ---
db = SQLAlchemy()
migrate = Migrate()

def get_database_uri():
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = "localhost"
    port = os.getenv("POSTGRES_PORT")
    dbname = os.getenv("POSTGRES_DB")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

# --- App Factory ---
def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

    with app.app_context():
        # Import models so Alembic can see them
        from . import models

        # Import and register blueprints
        from . import routes
        app.register_blueprint(routes.api_bp)

    return app