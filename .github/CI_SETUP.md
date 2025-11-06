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

| Secret Name | Description | Example Value | Default |
|------------|-------------|---------------|---------|
| `CI_POSTGRES_USER` | PostgreSQL username for CI tests | `ci_test_user` | `test_user` |
| `CI_POSTGRES_PASSWORD` | PostgreSQL password for CI tests | `secure_password_123` | `test_password` |
| `CI_POSTGRES_DB` | PostgreSQL database name | `ci_clarity_test` | `test_clarity_ai` |
| `CI_SUPERTOKENS_API_KEY` | SuperTokens API key for CI | `st_test_key_abc123` | `test_api_key` |

### Optional Secrets (for Integration Testing)

| Secret Name | Description | When to Use |
|------------|-------------|-------------|
| `OPENAI_API_KEY` | OpenAI API key | When testing LLM features with real API |
| `LANGCHAIN_API_KEY` | LangChain API key | When using LangChain tracing in tests |

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

## Security Best Practices

- **Never commit secrets** to the repository
- **Use different credentials** for CI than production
- **Rotate secrets regularly** (every 90 days recommended)
- **Limit secret access** to only necessary workflows
- **Use least privilege** - only add secrets you actually need

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

## Default Behavior

If you don't configure any secrets or variables, the workflow uses these defaults:

```yaml
# Database
POSTGRES_USER: test_user
POSTGRES_PASSWORD: test_password
POSTGRES_DB: test_clarity_ai

# SuperTokens
SUPERTOKENS_API_KEY: test_api_key

# Application
APP_NAME: Clarity AI Test
API_DOMAIN: http://localhost:5000
WEBSITE_DOMAIN: http://localhost:5173

# Versions
NODE_VERSION: 20.x
PYTHON_VERSION: 3.11
```

These defaults are suitable for basic CI testing and will work without any configuration.
