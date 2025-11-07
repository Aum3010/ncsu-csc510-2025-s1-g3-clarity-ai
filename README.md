[![DOI](https://zenodo.org/badge/1080501217.svg)](https://doi.org/10.5281/zenodo.17547339)  [![CI Pipeline](https://github.com/Aum3010/ncsu-csc510-2025-s1-g3-clarity-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Aum3010/ncsu-csc510-2025-s1-g3-clarity-ai/actions/workflows/ci.yml)


# 💡 Clarity AI: Intelligent Requirements Analysis

Clarity AI is a full-stack application that leverages Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) to transform unstructured discussions (like meeting transcripts or raw feature ideas) into structured, high-quality software requirements, user stories, and acceptance criteria.

We aim to eliminate ambiguity and contradictions in the planning phase, enabling development teams to build the right software with confidence.

TL;DR  - This is what we wished we had when we made it, so we made it for everyone to use!

## 🚀 Tech Stack

Clarity AI is a microservices application running via Docker Compose.

* **Backend (API & AI Core):** Python 3.11, Flask, SQLAlchemy, Pydantic.
* **Database (Persistence & Vector DB):** PostgreSQL with the `pgvector` extension for RAG context storage.
* **Frontend (UI):** Node.js, React, and Vite.
* **Authentication:** SuperTokens.

## Features
- **Passwordless Authentication**: Email-based OTP login powered by SuperTokens
- **User Profile Management**: Complete user profiles with role-based access control
- **Document Management**: Upload and manage project documents
- **AI-Powered Requirements**: Generate structured requirements from unstructured documents
- **Dashboard**: Overview of project requirements and documents
- **RAG-based Analysis**: Uses Retrieval-Augmented Generation to reduce the risk of LLM hallucinations.
- **Ambiguity Detection**: Identifies ambiguous statements within requirements and flags it for the user.
- **Contradiction Identification**: Identifies pairs of contradicting requirements and flags it for the user.

## Made by NCSU CSC-510 Section 001 Group 3
- Aum Pandya 
- Pranav Bhagwat
- Tayo Olukotun 


# Repo Information

## Project Structure

This repository is a monorepo containing:

* `/backend` : The Python (Flask) API, database logic, LLM processing, and SuperTokens authentication.
* `/frontend` : The React user interface with SuperTokens passwordless authentication.
* `/backend/tests` : Test suite for evaluating the frontend and backend features.


# Quick Start Guide (Recommended)

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

# Troubleshooting

## Backend Issues
- **Database connection errors**: Ensure PostgreSQL is running and credentials in `.env` are correct
- **SuperTokens errors**: Make sure SuperTokens Core is running on port 3567
- **Migration errors**: Run `flask db upgrade` to apply latest migrations

## Frontend Issues
- **CORS errors**: Verify `VITE_SUPERTOKENS_API_DOMAIN` matches your backend URL
- **Authentication errors**: Check that SuperTokens Core is accessible
- **Build errors**: Delete `node_modules` and run `npm install` again

## Docker Issues
- **Port conflicts**: Ensure ports 5000, 5173, 5432, and 3567 are available
- **Container errors**: Run `docker compose down -v` to clean up and restart

# Development Processes

## Running Tests
```bash
cd backend
python -m pytest
```

## Database Migrations
```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

## Code Structure
- `backend/app/routes.py`: API endpoints
- `backend/app/auth_service.py`: SuperTokens authentication logic
- `backend/app/models.py`: Database models
- `frontend/src/lib/auth-context.jsx`: Authentication state management
- `frontend/src/lib/supertokens-config.js`: SuperTokens frontend configuration

# Continuous Integration (CI)

This project uses **GitHub Actions** for automated testing and code quality checks. The CI pipeline runs automatically on every push and pull request to ensure code quality and catch issues early.

## What Gets Tested

The CI pipeline runs two parallel jobs:

#### Frontend Tests
- **Linting**: ESLint checks for code quality and style issues
- **Unit Tests**: Vitest runs all frontend tests
- **Build Verification**: Vite build ensures the application compiles successfully

#### Backend Tests
- **Unit & Integration Tests**: Pytest runs all backend tests with a real PostgreSQL database
- **Database Migrations**: Verifies migrations run successfully
- **Syntax Verification**: Checks Python syntax on main application files

### When CI Runs

- **On Push**: Every time you push code to any branch
- **On Pull Request**: When PRs are opened, updated, or reopened
- **Manual Trigger**: Can be run manually from the Actions tab

### Viewing CI Results

1. **In Pull Requests**: Status checks appear at the bottom of the PR
   - ✅ Green checkmark = All tests passed
   - ❌ Red X = One or more tests failed
   - 🟡 Yellow dot = Tests are running

2. **In the Actions Tab**: Click "Actions" in the repository to see all workflow runs
   - View detailed logs for each job
   - See which specific tests failed
   - Check execution time and performance

3. **Status Badges**: Check the workflow status at the top of the repository

### Interpreting CI Failures

If your CI pipeline fails, follow these steps:

1. **Click on the failed check** in your PR to view the logs
2. **Identify which job failed**: Frontend or Backend
3. **Read the error message** in the logs
4. **Run tests locally** to reproduce the issue:
   ```bash
   # Frontend
   cd frontend
   npm run lint    # Check linting errors
   npm run test    # Run tests
   npm run build   # Verify build
   
   # Backend
   cd backend
   pytest -v       # Run tests with verbose output
   ```
5. **Fix the issue** and push your changes
6. **CI will automatically re-run** on the new commit

### Common CI Issues and Solutions

### Frontend Issues

**Linting Errors**
```bash
# Problem: ESLint found code style issues
# Solution: Run ESLint locally and fix issues
cd frontend
npm run lint

# Auto-fix many issues
npm run lint -- --fix
```

**Test Failures**
```bash
# Problem: Frontend tests are failing
# Solution: Run tests locally to debug
cd frontend
npm run test

# Run specific test file
npm run test -- path/to/test-file.test.js
```

**Build Failures**
```bash
# Problem: Vite build is failing
# Solution: Run build locally to see errors
cd frontend
npm run build

# Common causes:
# - TypeScript errors
# - Missing dependencies
# - Import path issues
```

### Backend Issues

**Test Failures**
```bash
# Problem: Backend tests are failing
# Solution: Run pytest locally with verbose output
cd backend
pytest -v

# Run specific test file
pytest tests/test_specific.py -v

# Run with print statements visible
pytest -v -s
```

**Database Migration Errors**
```bash
# Problem: Migrations are failing in CI
# Solution: Test migrations locally
cd backend
flask db upgrade

# If migrations are out of sync
flask db downgrade
flask db upgrade
```

**Import/Syntax Errors**
```bash
# Problem: Python syntax errors
# Solution: Check syntax locally
cd backend
python -m py_compile app/main.py

# Or use a linter
flake8 app/
```

### Service Container Issues

**PostgreSQL Connection Errors**
- CI uses a PostgreSQL service container
- If tests fail with connection errors, the health check may have failed
- Check the "Wait for PostgreSQL" step in the logs

**SuperTokens Connection Errors**
- CI uses a SuperTokens service container
- If auth tests fail, check the "Wait for SuperTokens" step
- SuperTokens takes longer to start (up to 30 seconds)

## Performance

The CI pipeline is optimized for speed:
- **Parallel Jobs**: Frontend and backend tests run simultaneously
- **Dependency Caching**: npm and pip dependencies are cached
- **Typical Runtime**: 3-5 minutes for most changes
- **Cache Hit**: ~30 seconds faster with cached dependencies

## Required Status Checks

Before merging a pull request:
- ✅ Frontend Tests must pass
- ✅ Backend Tests must pass
- ✅ All linting checks must pass
- ✅ Build verification must succeed

These checks are enforced by branch protection rules on the `main` branch.

## Running CI Locally

To run the same checks locally before pushing:

```bash
# Frontend checks
cd frontend
npm ci                 # Clean install (like CI)
npm run lint          # Linting
npm run test          # Tests
npm run build         # Build

# Backend checks
cd backend
pip install -r requirements.txt
pytest -v             # Tests
python -m py_compile app/main.py  # Syntax check
```

## CI Configuration

The CI pipeline is defined in `.github/workflows/ci.yml`. Key features:

- **Concurrency Control**: Cancels outdated workflow runs when new commits are pushed
- **Caching**: Speeds up runs by caching dependencies
- **Service Containers**: Provides PostgreSQL and SuperTokens for integration tests
- **Status Reporting**: Posts detailed results to pull requests
- **Secrets & Variables**: Uses GitHub repository secrets and variables for configuration

### Required GitHub Secrets

Configure these in **Repository Settings > Secrets and variables > Actions > Secrets**:

**SuperTokens Database:**
| Secret Name | Description | Default (if not set) |
|------------|-------------|---------------------|
| `CI_SUPERTOKENS_POSTGRES_USER` | PostgreSQL username for SuperTokens database | `supertokens_user` |
| `CI_SUPERTOKENS_POSTGRES_PASSWORD` | PostgreSQL password for SuperTokens database | `supertokens_password` |
| `CI_SUPERTOKENS_POSTGRES_DB` | PostgreSQL database name for SuperTokens | `supertokens` |

**Application Database:**
| Secret Name | Description | Default (if not set) |
|------------|-------------|---------------------|
| `CI_APP_POSTGRES_USER` | PostgreSQL username for application database | `test_user` |
| `CI_APP_POSTGRES_PASSWORD` | PostgreSQL password for application database | `test_password` |
| `CI_APP_POSTGRES_DB` | PostgreSQL database name for application | `test_clarity_ai` |

**Authentication:**
| Secret Name | Description | Default (if not set) |
|------------|-------------|---------------------|
| `CI_SUPERTOKENS_API_KEY` | SuperTokens API key for CI tests | `test_api_key` |

**External Services (Optional):**
| Secret Name | Description | When to Set |
|------------|-------------|-------------|
| `OPENAI_API_KEY` | OpenAI API key | Only if testing RAG features with real API (tests use mocks by default) |
| `LANGCHAIN_API_KEY` | LangChain API key | Only if using LangChain tracing in tests (rarely needed) |

### Required GitHub Variables

Configure these in **Repository Settings > Secrets and variables > Actions > Variables**:

| Variable Name | Description | Default (if not set) |
|--------------|-------------|---------------------|
| `CI_APP_NAME` | Application name for tests | `Clarity AI Test` |
| `CI_API_DOMAIN` | Backend API domain | `http://localhost:5000` |
| `CI_WEBSITE_DOMAIN` | Frontend domain | `http://localhost:5173` |
| `CI_NODE_VERSION` | Node.js version to use | `20.x` |
| `CI_PYTHON_VERSION` | Python version to use | `3.11` |

**Note**: The workflow includes fallback defaults for all secrets and variables, so it will work out of the box. Configure custom values only if you need different settings.

For detailed setup instructions, see [.github/CI_SETUP.md](.github/CI_SETUP.md).

For more details about the workflow, see the workflow file comments.

# Contributing 

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests locally to ensure everything works
4. Push your changes (CI will run automatically)
5. Ensure all CI checks pass
6. Submit a pull request


## License

This project is ![MIT-licensed](LICENSE).
It was created as a part of the CSC-510 coursework at North Carolina State University, Raleigh. 