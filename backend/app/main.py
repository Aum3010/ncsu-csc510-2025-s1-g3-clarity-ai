from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    """The main home/index route."""
    return "Hello, Clarity AI!"

if __name__ == '__main__':
    app.run(debug=True)