# CI/CD Setup Guide

This guide explains how to configure GitHub Secrets and Variables for the CI/CD pipeline.

## Quick Start

The CI pipeline works out of the box with default test credentials. You only need to configure custom secrets/variables if:
- You want to use different test credentials
- You need to test with real external services (OpenAI, LangChain)
- You want to customize Node.js or Python versions

## Setting Up Secrets

1. Go to your repository on GitHub
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click the **Secrets** tab
4. Click **New repository secret**
5. Add each secret from the table below

### Required Secrets

**SuperTokens Database Credentials:**

| Secret Name | Description | Example Value | Default |
|------------|-------------|---------------|---------|
| `CI_SUPERTOKENS_POSTGRES_USER` | PostgreSQL username for SuperTokens database | `st_user` | `supertokens_user` |
| `CI_SUPERTOKENS_POSTGRES_PASSWORD` | PostgreSQL password for SuperTokens database | `st_secure_pass` | `supertokens_password` |
| `CI_SUPERTOKENS_POSTGRES_DB` | PostgreSQL database name for SuperTokens | `st_database` | `supertokens` |

**Application Database Credentials:**

| Secret Name | Description | Example Value | Default |
|------------|-------------|---------------|---------|
| `CI_APP_POSTGRES_USER` | PostgreSQL username for application database | `app_test_user` | `test_user` |
| `CI_APP_POSTGRES_PASSWORD` | PostgreSQL password for application database | `app_secure_pass` | `test_password` |
| `CI_APP_POSTGRES_DB` | PostgreSQL database name for application | `app_test_db` | `test_clarity_ai` |

**Authentication:**

| Secret Name | Description | Example Value | Default |
|------------|-------------|---------------|---------|
| `CI_SUPERTOKENS_API_KEY` | SuperTokens API key for CI | `st_test_key_abc123` | `test_api_key` |

### Optional Secrets (for Integration Testing)

These secrets are **not required** for CI to run. Only set them if you need to test with real external services.

| Secret Name | Description | When to Use | Default Behavior |
|------------|-------------|-------------|------------------|
| `OPENAI_API_KEY` | OpenAI API key | When testing RAG/LLM features with real OpenAI API | Tests use mocks or skip API-dependent tests |
| `LANGCHAIN_API_KEY` | LangChain API key | When using LangChain tracing/monitoring in tests | Not used unless explicitly configured |

**Important Notes:**
- **Cost Consideration**: Setting `OPENAI_API_KEY` will make real API calls, which cost money on every CI run
- **Test Design**: Your tests should be designed to work without these keys (using mocks/stubs)
- **Integration Testing**: Only set these keys if you specifically want to run integration tests against real services
- **Recommended**: Leave these unset for regular CI runs, only use them for special integration test workflows

## Setting Up Variables

1. Go to your repository on GitHub
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click the **Variables** tab
4. Click **New repository variable**
5. Add each variable from the table below

### Configuration Variables

| Variable Name | Description | Example Value | Default |
|--------------|-------------|---------------|---------|
| `CI_APP_NAME` | Application name for tests | `Clarity AI Test` | `Clarity AI Test` |
| `CI_API_DOMAIN` | Backend API domain | `http://localhost:5000` | `http://localhost:5000` |
| `CI_WEBSITE_DOMAIN` | Frontend domain | `http://localhost:5173` | `http://localhost:5173` |
| `CI_NODE_VERSION` | Node.js version | `20.x` or `18.x` | `20.x` |
| `CI_PYTHON_VERSION` | Python version | `3.11` or `3.10` | `3.11` |

## Example: Adding a Secret

```bash
# Via GitHub UI:
1. Settings > Secrets and variables > Actions > Secrets
2. Click "New repository secret"
3. Name: CI_POSTGRES_PASSWORD
4. Secret: your_secure_password
5. Click "Add secret"
```

## Example: Adding a Variable

```bash
# Via GitHub UI:
1. Settings > Secrets and variables > Actions > Variables
2. Click "New repository variable"
3. Name: CI_NODE_VERSION
4. Value: 20.x
5. Click "Add variable"
```

## Verifying Configuration

After adding secrets/variables:

1. Go to **Actions** tab in your repository
2. Click on the latest workflow run
3. Expand any job to see the environment variables being used
4. Secrets will show as `***` (masked)
5. Variables will show their actual values

## Testing Strategy for External APIs

### Recommended Approach

**For Regular CI Runs (Default):**
- Don't set `OPENAI_API_KEY` or `LANGCHAIN_API_KEY`
- Tests should use mocks/stubs for external API calls
- This keeps CI fast and free
- Prevents accidental API costs

**For Integration Testing (Optional):**
- Create a separate workflow (e.g., `integration-tests.yml`)
- Only run on specific branches or manual trigger
- Set the API keys only for that workflow
- Monitor API usage and costs

### Example Test Pattern

```python
# Good: Test works with or without real API key
def test_generate_requirements():
    if os.getenv('OPENAI_API_KEY'):
        # Run real integration test
        result = generate_requirements_with_openai(text)
    else:
        # Use mock for unit test
        with patch('openai.ChatCompletion.create') as mock:
            mock.return_value = mock_response
            result = generate_requirements_with_openai(text)
    
    assert result is not None
```

## Security Best Practices

- **Never commit secrets** to the repository
- **Use different credentials** for CI than production
- **Rotate secrets regularly** (every 90 days recommended)
- **Limit secret access** to only necessary workflows
- **Use least privilege** - only add secrets you actually need
- **Monitor API costs** - if using real API keys, set up billing alerts

## Troubleshooting

### Secrets Not Working

- Ensure secret names match exactly (case-sensitive)
- Check that secrets are added at the repository level, not organization level
- Verify the workflow has permission to access secrets

### Variables Not Working

- Ensure variable names match exactly (case-sensitive)
- Variables are not encrypted - don't use them for sensitive data
- Check the Actions tab to see what values are being used

### Service Container Issues

If PostgreSQL or SuperTokens containers fail to start:
- Check that credentials in secrets match those in service container configuration
- The workflow automatically syncs credentials between job env and service containers
- Review the "Wait for PostgreSQL" and "Wait for SuperTokens" step logs

### Database Setup

The CI workflow uses a two-database setup that mirrors your docker-compose.yml:

1. **SuperTokens Database**: Created automatically by the postgres container
   - Used exclusively by SuperTokens for authentication data
   - Credentials: `CI_SUPERTOKENS_POSTGRES_*` secrets

2. **Application Database**: Created by the "Create application database" step
   - Used by your Flask application for business data
   - Credentials: `CI_APP_POSTGRES_*` secrets
   - Includes pgvector extension for AI/ML features

This separation ensures SuperTokens and application data remain isolated, matching your local development environment.

## Default Behavior

If you don't configure any secrets or variables, the workflow uses these defaults:

```yaml
# SuperTokens Database (matches docker-compose.yml)
SUPERTOKENS_POSTGRES_USER: supertokens_user
SUPERTOKENS_POSTGRES_PASSWORD: supertokens_password
SUPERTOKENS_POSTGRES_DB: supertokens

# Application Database (matches docker-compose.yml)
APP_POSTGRES_USER: test_user
APP_POSTGRES_PASSWORD: test_password
APP_POSTGRES_DB: test_clarity_ai

# SuperTokens Authentication
SUPERTOKENS_API_KEY: test_api_key

# Application Configuration
APP_NAME: Clarity AI Test
API_DOMAIN: http://localhost:5000
WEBSITE_DOMAIN: http://localhost:5173

# Runtime Versions
NODE_VERSION: 20.x
PYTHON_VERSION: 3.11
```

These defaults mirror your docker-compose.yml configuration and are suitable for basic CI testing without any additional setup.
