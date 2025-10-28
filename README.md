# Clarity AI (CSC-510 Section 1 Group 3)

Clarity AI is a tool that uses LLMs to create, analyze, refine, and structure project requirements from unstructured team discussions. It turns messy meeting notes into a structured dashboard of user stories and technical requirements.

## Team Members
Aum Pandya 
Pranav Bhagwat
Tayo Olukotun 

## Project Structure

This repository is a monorepo containing:

* `/backend`: The Python (Flask) API, database logic, LLM processing, and SuperTokens authentication.
* `/frontend`: The React user interface with SuperTokens passwordless authentication.

## Features

- **Passwordless Authentication**: Email-based OTP login powered by SuperTokens
- **User Profile Management**: Complete user profiles with role-based access control
- **Document Management**: Upload and manage project documents
- **AI-Powered Requirements**: Generate structured requirements from unstructured documents
- **Dashboard**: Overview of project requirements and documents

---

## Quick Start with Docker (Recommended)

The easiest way to run the application is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/Aum3010/ncsu-csc510-2025-s1-g3-clarity-ai.git
cd ncsu-csc510-2025-s1-g3-clarity-ai

# Copy environment files
cp .env.example .env
cp frontend/.env.example frontend/.env

# Edit .env files with your configuration (see Environment Variables section below)

# Start all services (backend, frontend, database, SuperTokens)
docker compose up
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:5000
- SuperTokens Core: http://localhost:3567

---

## Manual Setup (Alternative)

If you prefer to run services manually without Docker:

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
    
2.  **Edit the .env file:** Open `.env` in your code editor and fill in the values.
    
    *   `POSTGRES_USER`: Your username (run `whoami` in terminal to find it).
    *   `POSTGRES_PORT`: The port from step 2 (e.g., 5433).
    *   `POSTGRES_DB`: clarity_ai
    *   `POSTGRES_PASSWORD`: Leave this blank for local development.
    *   `OPENAI_API_KEY`: Your OpenAI API key.
    *   `SUPERTOKENS_CONNECTION_URI`: http://localhost:3567 (or your SuperTokens Core URL)
    *   `SUPERTOKENS_API_KEY`: Your SuperTokens API key (optional for local development)
    *   `TWILIO_ACCOUNT_SID`: Your Twilio Account SID (for OTP emails)
    *   `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token
    *   `TWILIO_VERIFY_SERVICE_SID`: Your Twilio Verify Service SID
        

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
cp .env.example .env
```

Edit `frontend/.env` and set:
- `VITE_API_URL`: http://localhost:5000 (backend API URL)
- `VITE_SUPERTOKENS_APP_NAME`: Clarity AI
- `VITE_SUPERTOKENS_API_DOMAIN`: http://localhost:5000
- `VITE_SUPERTOKENS_WEBSITE_DOMAIN`: http://localhost:5173

### 3\. Install Dependencies

This will install all the necessary Node.js packages defined in package.json.

```bash
npm install
```

### 4\. Run the Development Server

This command starts the React development server.

```bash
npm run dev
```

Your React application is now running and accessible at **http://localhost:5173**. The app is configured to automatically connect to your backend running on port 5000.

## Running the Full Application (Manual Setup)

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

---

## Authentication

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

---

## Environment Variables

### Backend (.env)
```env
# Database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=
POSTGRES_DB=clarity_ai
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# SuperTokens
SUPERTOKENS_CONNECTION_URI=http://localhost:3567
SUPERTOKENS_API_KEY=

# Twilio (for OTP emails)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_VERIFY_SERVICE_SID=your_twilio_verify_service_sid

# Flask
FLASK_ENV=development
SECRET_KEY=your_secret_key
```

### Frontend (frontend/.env)
```env
VITE_API_URL=http://localhost:5000
VITE_SUPERTOKENS_APP_NAME=Clarity AI
VITE_SUPERTOKENS_API_DOMAIN=http://localhost:5000
VITE_SUPERTOKENS_WEBSITE_DOMAIN=http://localhost:5173
```

---

## Troubleshooting

### Backend Issues
- **Database connection errors**: Ensure PostgreSQL is running and credentials in `.env` are correct
- **SuperTokens errors**: Make sure SuperTokens Core is running on port 3567
- **Migration errors**: Run `flask db upgrade` to apply latest migrations

### Frontend Issues
- **CORS errors**: Verify `VITE_SUPERTOKENS_API_DOMAIN` matches your backend URL
- **Authentication errors**: Check that SuperTokens Core is accessible
- **Build errors**: Delete `node_modules` and run `npm install` again

### Docker Issues
- **Port conflicts**: Ensure ports 5000, 5173, 5432, and 3567 are available
- **Container errors**: Run `docker compose down -v` to clean up and restart

---

## Development

### Running Tests
```bash
cd backend
python -m pytest
```

### Database Migrations
```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

### Code Structure
- `backend/app/routes.py`: API endpoints
- `backend/app/auth_service.py`: SuperTokens authentication logic
- `backend/app/models.py`: Database models
- `frontend/src/lib/auth-context.jsx`: Authentication state management
- `frontend/src/lib/supertokens-config.js`: SuperTokens frontend configuration

---

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests to ensure everything works
4. Submit a pull request

---

## License

This project is part of CSC-510 coursework at NC State University.