import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Import Migrate
from dotenv import load_dotenv

load_dotenv()

# --- Database Setup ---
db = SQLAlchemy()
migrate = Migrate()  # Initialize Migrate

def get_database_uri():
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = "localhost"
    port = os.getenv("POSTGRES_PORT")
    dbname = os.getenv("POSTGRES_DB")
    return f"postgresql://{user}@{host}:{port}/{dbname}"

# --- App Factory ---
def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)  # Link migrate to the app and db

    # Import models *after* db is initialized but *before* routes
    # This ensures migrate knows about your models
    with app.app_context():
        from . import models

    # --- Register Blueprints (Routes) ---
    @app.route('/')
    def home():
        return "Hello, Clarity AI!"

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)