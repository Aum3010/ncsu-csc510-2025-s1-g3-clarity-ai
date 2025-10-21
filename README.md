# Clarity AI (CSC-510 Section 1 Group 3)

Clarity AI is a tool that uses LLMs to create, analyze, refine, and structure project requirements from unstructured team discussions. It turns messy meeting notes into a structured dashboard of user stories and technical requirements.

## Team Members
Aum Pandya 
Pranav Bhagwat
Tayo Olukotun 

## Project Structure

This repository is a monorepo containing:

* `/backend`: The Python (Flask) API, database logic, and LLM processing.
* `/frontend`: The React user interface.


---

## Backend Setup 

Follow these steps to get the backend API running on your local machine.

### 1. Clone the Repository

```bash
git clone https://github.com/Aum3010/ncsu-csc510-2025-s1-g3-clarity-ai.git \\
cd ncsu-csc510-2025-s1-g3-clarity-ai
```

### Set Up the Database (Postgres.app)

1.  **Install & Open Postgres.app.**
    
2.  Click **"Initialize"** to start a new server.
    
3.  **Check the Port:** The app will try to run on port 5432. If it says "Port 5432 is already in use," click **"Server Settings..."** and change the port to **5433**.
    
4.  **Open psql:** In the app window, double-click the default database (named after your username).
    
5. Create our project database `CREATE DATABASE clarity_ai;`
6. Connect to the new `database c clarity_ai` 
7. Enable the pgvector extension for AI embeddings `CREATE EXTENSION IF NOT EXISTS vector;`
    

### 3\. Set Up the Python Environment

1.  `cd backend`
    
2.  `conda create --name clarity-backend python=3.11`
    
3.  `conda activate clarity-backend`
    

### 4\. Configure Environment Variables

1.  `cp .env.example .env`
    
2.  **Edit the .env file:** Open backend/.env in your code editor and fill in the values.
    
    *   POSTGRES\_USER: Your username (run whoami in terminal to find it).
        
    *   POSTGRES\_PORT: The port from step 2 (e.g., 5433).
        
    *   POSTGRES\_DB: clarity\_ai
        
    *   POSTGRES\_PASSWORD: Leave this blank.
        
    *   OPENAI\_API\_KEY: Your OpenAI API key.
        

### 5\. Install Dependencies & Run Database Migrations

1.  `python -m pip install -r requirements.txt`
    
2. Set the FLASK\_APP environment variable for the current session
   `export FLASK_APP=wsgi.py` 
3.  Initialize the database migration scripts `python -m flask db init`
    
4.  `python -m flask db upgrade`
    

### 6\. Run Tests and Start the Server

1.  `python -m pytest`
2.  You should see all tests pass!
    
3.  `python wsgi.py` 
4.  Your Flask server is now running on http://127.0.0.1:5000.
    

## Frontend Setup
--------------

### 1\. Navigate to the Frontend Directory

Open a **new, separate terminal window** and navigate to the frontend folder.
`   cd frontend   `

### 2\. Install Dependencies

This will install all the necessary Node.js packages defined in package.json.

`   npm install   `

### 3\. Run the Development Server

This command starts the React development server.

`   npm run dev   `

Your React application is now running and accessible at **http://localhost:5173**. The app is configured to automatically connect to your backend running on port 5000.

Running the Full Application
----------------------------

To work on the project, you will need **two terminals** running simultaneously:

1.  cd backendconda activate clarity-backendpython wsgi.py
    
2.  cd frontendnpm run dev
    

Open **http://localhost:5173** in your web browser to use the application.