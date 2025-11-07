# /.../backend/app/seed.py
import os
import sys
from datetime import datetime

# --- This is the new, important part ---
# 1. Get the absolute path of the current file (e.g., /.../backend/app/seed.py)
current_file_path = os.path.abspath(__file__)
# 2. Get the path of the directory this file is in (e.g., /.../backend/app)
current_dir = os.path.dirname(current_file_path)
# 3. Get the path of the parent directory (e.g., /.../backend)
parent_dir = os.path.dirname(current_dir)

# 4. Add the parent directory to the system path
# This allows us to import from 'app.' as if we were in the 'backend' folder
sys.path.insert(0, parent_dir)
# --- End of new part ---

try:
    # Now we can import from app.main and app.lexicon_manager
    from app.main import create_app, db
    from app.lexicon_manager import LexiconManager

except ImportError as e:
    print("--- IMPORT ERROR ---")
    print(f"Failed to import modules: {e}")
    print(f"Current Path: {current_dir}")
    print(f"Parent Path (added to sys.path): {parent_dir}")
    print("Please ensure your 'main.py' and 'lexicon_manager.py' are in the 'app' folder.")
    sys.exit(1)


# We must call create_app() to get an app instance
app = create_app()

# Now we use the 'app_context' from the app we just created
with app.app_context():
    print("Application context loaded. Seeding lexicon...")
    
    try:
        # Get the LexiconManager instance
        lexicon_manager = LexiconManager()
        
        # Call the seed function
        added_count = lexicon_manager.seed_default_lexicon()
        
        print(f"Successfully added {added_count} new terms to the database.")
        print("Lexicon seeding complete!")
    
    except Exception as e:
        db.session.rollback()
        print(f"An error occurred while seeding: {e}")
        print("Database transaction was rolled back.")