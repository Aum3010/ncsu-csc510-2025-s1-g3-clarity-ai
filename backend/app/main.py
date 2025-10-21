from flask import Flask
from flask_cors import CORS  # Import CORS

# Create the Flask app instance
app = Flask(__name__)

# Enable CORS for all routes, allowing requests from our frontend
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

@app.route('/')
def home():
    """The main home/index route."""
    return "Hello, Clarity AI!"

# This allows you to run the app directly with 'python app/main.py'
if __name__ == '__main__':
    app.run(debug=True)