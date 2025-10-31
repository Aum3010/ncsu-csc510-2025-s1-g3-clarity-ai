/**
 * Basic tests for SuperTokens configuration
 * These tests verify that the configuration is properly set up
 */

import { describe, it, expect } from 'vitest';

// Import the functions to test they're properly exported
import {
  sendPasswordlessCode,
  consumePasswordlessCode,
  resendPasswordlessCode,
  doesSessionExist,
  signOut,
  getAccessToken,
  getUserId,
  getClaimValue,
  validateSession,
} from '../supertokens-config.js';

import { SUPERTOKENS_CONFIG, API_ENDPOINTS, ROUTES, OTP_CONFIG } from '../constants.js';

describe('SuperTokens Configuration', () => {
  it('should export all required authentication functions', () => {
    expect(typeof sendPasswordlessCode).toBe('function');
    expect(typeof consumePasswordlessCode).toBe('function');
    expect(typeof resendPasswordlessCode).toBe('function');
    expect(typeof doesSessionExist).toBe('function');
    expect(typeof signOut).toBe('function');
    expect(typeof getAccessToken).toBe('function');
    expect(typeof getUserId).toBe('function');
    expect(typeof getClaimValue).toBe('function');
    expect(typeof validateSession).toBe('function');
  });

  it('should have proper configuration constants', () => {
    expect(SUPERTOKENS_CONFIG.APP_NAME).toBe('Krexin Frontend');
    expect(SUPERTOKENS_CONFIG.API_BASE_PATH).toBe('/auth');
    expect(SUPERTOKENS_CONFIG.WEBSITE_BASE_PATH).toBe('/auth');
    expect(typeof SUPERTOKENS_CONFIG.API_DOMAIN).toBe('string');
    expect(typeof SUPERTOKENS_CONFIG.WEBSITE_DOMAIN).toBe('string');
    expect(typeof SUPERTOKENS_CONFIG.SESSION_SCOPE).toBe('string');
  });

  it('should have proper API endpoints configuration', () => {
    expect(typeof API_ENDPOINTS.CORE_API).toBe('string');
    expect(typeof API_ENDPOINTS.AUTH_API).toBe('string');
    expect(API_ENDPOINTS.AUTH_API).toContain('/auth');
  });

  it('should have proper routes configuration', () => {
    expect(ROUTES.LOGIN).toBe('/login');
    expect(ROUTES.DASHBOARD).toBe('/dashboard');
    expect(ROUTES.PROFILE_COMPLETION).toBe('/complete-profile');
  });

  it('should have proper OTP configuration', () => {
    expect(OTP_CONFIG.RESEND_COOLDOWN).toBe(60);
    expect(OTP_CONFIG.MAX_ATTEMPTS).toBe(5);
  });
});