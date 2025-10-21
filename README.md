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

## Prerequisites

Before you begin, you will need the following tools installed on your (Mac) development machine:

1.  **Git:** For cloning the repository.
2.  **Conda (Miniforge/Anaconda):** For managing our Python environment.
3.  **[Postgres.app](https://postgresapp.com/):** The easiest way to run a local PostgreSQL server on macOS.

---

## Backend Setup (macOS)

Follow these steps to get the backend API running on your local machine.

### 1. Clone the Repository

```bash
git clone [https://github.com/Aum3010/ncsu-csc510-2025-s1-g3-clarity-ai.git](https://github.com/Aum3010/ncsu-csc510-2025-s1-g3-clarity-ai.git)
cd ncsu-csc510-2025-s1-g3-clarity-ai
```

### Set Up the Database (Postgres.app)

1.  **Install & Open Postgres.app.**
    
2.  Click **"Initialize"** to start a new server.
    
3.  **Check the Port:** The app will try to run on port 5432. If it says "Port 5432 is already in use," click **"Server Settings..."** and change the port to **5433**.
    
4.  **Open psql:** In the app window, double-click the default database (named after your username).
    
5.  SQL-- 1. Create our project databaseCREATE DATABASE clarity\_ai;-- 2. Connect to the new database\\c clarity\_ai-- 3. Enable the pgvector extension for AI embeddingsCREATE EXTENSION IF NOT EXISTS vector;
    

### 3\. Set Up the Python Environment

1.  Bashcd backend
    
2.  Bashconda create --name clarity-backend python=3.11
    
3.  Bashconda activate clarity-backend
    

### 4\. Configure Environment Variables

1.  Bashcp .env.example .env
    
2.  **Edit the .env file:** Open backend/.env in your code editor and fill in the values.
    
    *   POSTGRES\_USER: Your username (run whoami in terminal to find it).
        
    *   POSTGRES\_PORT: The port from step 2 (e.g., 5433).
        
    *   POSTGRES\_DB: clarity\_ai
        
    *   POSTGRES\_PASSWORD: Leave this blank.
        
    *   OPENAI\_API\_KEY: Your personal OpenAI API key.
        

### 5\. Install Dependencies & Run Tests

1.  Bashpython -m pip install -r requirements.txt
    
2.  Bashpython -m pytestYou should see all tests pass!
    

### 6\. Run the Application

`   python app/main.py   `

Your Flask server is now running. You can view the "Hello World" route by opening http://127.0.0.1:5000 in your browser.

Frontend Setup
--------------

