# SuperTokens Configuration

This directory contains the SuperTokens authentication configuration and utilities for the Krexin frontend application.

## Files

- `supertokens-config.js` - Main SuperTokens configuration and authentication functions
- `constants.js` - Configuration constants and API endpoints
- `index.js` - Main exports for the lib directory

## Usage

### Basic Authentication Functions

```javascript
import {
  sendPasswordlessCode,
  consumePasswordlessCode,
  resendPasswordlessCode,
  doesSessionExist,
  signOut,
  validateSession
} from './lib/supertokens-config.js';

// Send OTP to email
await sendPasswordlessCode('user@example.com');

// Verify OTP
const result = await consumePasswordlessCode('123456');

// Check if session exists
const hasSession = await doesSessionExist();

// Sign out user
await signOut();
```

### Configuration Constants

```javascript
import { SUPERTOKENS_CONFIG, API_ENDPOINTS, ROUTES } from './lib/constants.js';

console.log(SUPERTOKENS_CONFIG.API_DOMAIN); // API domain
console.log(API_ENDPOINTS.CORE_API); // Core API endpoint
console.log(ROUTES.LOGIN); // Login route
```

## Environment Variables

The following environment variables are used:

- `VITE_API_DOMAIN` - Backend API domain (default: http://localhost:5000)
- `VITE_WEBSITE_DOMAIN` - Frontend domain (default: http://localhost:5173)
- `VITE_SESSION_SCOPE` - Session scope (default: localhost)

## Features

- **Passwordless Authentication**: Email-based OTP authentication
- **Session Management**: Header-based token transfer with automatic refresh
- **Error Handling**: Comprehensive error handling for all authentication operations
- **Event Logging**: Built-in logging for authentication events
- **Type Safety**: JSDoc annotations for better IDE support

## Testing

Run tests with:

```bash
npm test
```

The configuration includes unit tests that verify:
- All authentication functions are properly exported
- Configuration constants are correctly set
- API endpoints are properly configured
- Routes and OTP settings are valid