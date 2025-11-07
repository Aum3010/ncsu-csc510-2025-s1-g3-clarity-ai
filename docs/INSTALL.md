# Manual Setup

If you prefer to run services manually without Docker:

## Backend Setup 

Follow these steps to get the backend API running on your local machine.

### 1. Clone the Repository

```bash
git clone https://github.com/Aum3010/ncsu-csc510-2025-s1-g3-clarity-ai.git \\
cd ncsu-csc510-2025-s1-g3-clarity-ai
```

### Set Up the Database (Postgres.app)

#### Install Postgres on macOS

1.  **Install & Open Postgres.app.**
    
2.  Click **"Initialize"** to start a new server.
    
3.  **Check the Port:** The app will try to run on port 5432. If it says "Port 5432 is already in use," click **"Server Settings..."** and change the port to **5433**.
    
4.  **Open psql:** In the app window, double-click the default database (named after your username).

#### Install Postgres on Linux (Ubuntu 22.04)

1. To install PostgreSQL, first refresh your server’s local package index: 
```
sudo apt install curl ca-certificates
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
. /etc/os-release
sudo sh -c "echo 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main' > /etc/apt/sources.list.d/pgdg.list"
sudo apt update
sudo apt install postgresql-18
sudo apt install postgresql-18-pgvector
```

2. After installation, verify that PostgreSQL is running and check its version:
`sudo systemctl status postgresql`

3. You should see output indicating that the service is active and running. To check the PostgreSQL version:
`sudo -u postgres psql -c "SELECT version();"`

4. Access the postgres shell by switching into postgres user.
```
sudo -i -u postgres
psql
```

    
5. Create our project database `CREATE DATABASE clarity_ai;`
6. Connect to the new `database c clarity_ai` 
7. Enable the pgvector extension for AI embeddings `CREATE EXTENSION IF NOT EXISTS vector;`
    

### 3\. Set Up the Python Environment

1.  `cd backend`
    
2.  `conda create --name clarity-backend python=3.11`
    
3.  `conda activate clarity-backend`
    

### 4\. Configure Environment Variables

1.  `cp .env.example .env`
    
2.  **Edit the .env file:** Open `.env` in your code editor and fill in the values.
    
    *   `POSTGRES_USER`: Your username (run `whoami` in terminal to find it).
    *   `POSTGRES_PORT`: The port from step 2 (e.g., 5433).
    *   `POSTGRES_DB`: clarity_ai
    *   `POSTGRES_PASSWORD`: Leave this blank for local development.
    *   `OPENAI_API_KEY`: Your OpenAI API key.
    *   `SUPERTOKENS_CONNECTION_URI`: http://localhost:3567
    *   `SUPERTOKENS_API_KEY`: Optional for local development
    *   `APP_NAME`: Clarity AI
    *   `API_DOMAIN`: http://localhost:5000
    *   `WEBSITE_DOMAIN`: http://localhost:5173
        

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
```bash
cd frontend
```

### 2\. Configure Frontend Environment

```bash
cp ../.env.example .env
```

Edit `frontend/.env` and set:
- `VITE_APP_NAME`: Clarity AI
- `VITE_API_DOMAIN`: http://localhost:5000
- `VITE_WEBSITE_DOMAIN`: http://localhost:5173
- `VITE_SESSION_SCOPE`: localhost

### 3\. Install Dependencies

This will install all the necessary Node.js packages defined in package.json.

```bash
npm install
```

If `npm` is not installed, follow the installation steps in:
- https://github.com/creationix/nvm for macOS or Linux
- https://github.com/coreybutler/nvm-windows for Windows

### 4\. Run the Development Server

This command starts the React development server.

```bash
npm run dev
```

Your React application is now running and accessible at **http://localhost:5173**. The app is configured to automatically connect to your backend running on port 5000.

## Running the full application

To work on the project manually, you will need **three terminals** running simultaneously:

### Terminal 1: SuperTokens Core

```bash
docker run -p 3567:3567 -d registry.supertokens.io/supertokens/supertokens-postgresql
```

### Terminal 2: Backend
```bash 
cd backend
conda activate clarity-backend
python wsgi.py
```

### Terminal 3: Frontend
```bash 
cd frontend
npm run dev
```

Open **http://localhost:5173** in your web browser to use the application.

## How to manage authentication

The application uses **SuperTokens Passwordless Authentication**:

1. Navigate to http://localhost:5173
2. Enter your email address
3. Receive a 6-digit OTP code via email
4. Enter the OTP to log in
5. Complete your profile (first time only)
6. Access the dashboard

### First-Time Users
- After OTP verification, you'll be prompted to complete your profile
- Fill in: First Name, Last Name, Company, and Job Title
- Your profile is saved and you won't need to complete it again

### Returning Users
- Simply enter your email and OTP
- You'll be redirected directly to the dashboard

## Environment Variables Setup

### Root (.env) - For Docker Compose
```env
# SuperTokens Database
SUPERTOKENS_POSTGRES_DB=supertokens
SUPERTOKENS_POSTGRES_USER=supertokens_user
SUPERTOKENS_POSTGRES_PASSWORD=supertokens_password

# Application Database
POSTGRES_DB=clarity_ai
POSTGRES_USER=clarity_user
POSTGRES_PASSWORD=clarity_password

# SuperTokens API
SUPERTOKENS_API_KEY=your-local-supertokens-api-key-here
```

### Backend (backend/.env)
```env
# Database
POSTGRES_USER=clarity_user
POSTGRES_PASSWORD=clarity_password
POSTGRES_DB=clarity_ai
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# SuperTokens
SUPERTOKENS_CONNECTION_URI=http://localhost:3567
SUPERTOKENS_API_KEY=your-local-supertokens-api-key-here
APP_NAME=Clarity AI
API_DOMAIN=http://localhost:5000
WEBSITE_DOMAIN=http://localhost:5173

# Session Configuration
SESSION_TIMEOUT=3600
OTP_EXPIRY=600
REFRESH_TIMEOUT=86400
```

### Frontend (frontend/.env)
```env
# Application Configuration
VITE_APP_NAME=Clarity AI
VITE_API_DOMAIN=http://localhost:5000
VITE_WEBSITE_DOMAIN=http://localhost:5173
VITE_SESSION_SCOPE=localhost

# Development
NODE_ENV=development
```