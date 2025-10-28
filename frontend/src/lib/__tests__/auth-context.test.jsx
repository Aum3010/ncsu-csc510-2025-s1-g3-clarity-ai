import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../auth-context.jsx';
import * as supertokensConfig from '../supertokens-config.js';
import apiService from '../api-service.js';
import { OTP_CONFIG } from '../constants.js';

// Mock SuperTokens functions
vi.mock('../supertokens-config.js');
vi.mock('../api-service.js');

describe('Authentication Context - OTP Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    supertokensConfig.validateSession.mockResolvedValue(false);
  });

  it('should send OTP successfully', async () => {
    supertokensConfig.sendPasswordlessCode.mockResolvedValue({
      status: 'OK',
      deviceId: 'device-123',
      preAuthSessionId: 'session-123',
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    let sendResult;
    await act(async () => {
      sendResult = await result.current.sendOTP('test@example.com');
    });

    expect(sendResult.success).toBe(true);
    expect(result.current.otpResendCooldown).toBe(OTP_CONFIG.RESEND_COOLDOWN);
  });

  it('should reject invalid email', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    await act(async () => {
      await expect(result.current.sendOTP('invalid')).rejects.toThrow('valid email');
    });
  });

  it('should verify OTP for new user', async () => {
    supertokensConfig.consumePasswordlessCode.mockResolvedValue({ status: 'OK' });
    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockRejectedValue(new Error('Not found'));

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    let verifyResult;
    await act(async () => {
      verifyResult = await result.current.verifyOTP('123456');
    });

    expect(verifyResult.isNewUser).toBe(true);
    expect(result.current.isAuthenticated).toBe(true);
  });
});

describe('Authentication Context - Session Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with valid session', async () => {
    const mockProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Test',
        last_name: 'User',
        user_profile: { company: 'Test Co', job_title: 'Dev' },
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(mockProfile);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user.email).toBe('test@example.com');
  });

  it('should sign out successfully', async () => {
    const mockProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Test',
        last_name: 'User',
        user_profile: { company: 'Test Co', job_title: 'Dev' },
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(mockProfile);
    supertokensConfig.signOut.mockResolvedValue({ status: 'OK' });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    await act(async () => {
      await result.current.signOut();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });
});

describe('Authentication Context - Permissions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should grant access to authenticated user', async () => {
    const mockProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Test',
        last_name: 'User',
        user_profile: { company: 'Test Co', job_title: 'Dev' },
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(mockProfile);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    let hasAccess;
    await act(async () => {
      hasAccess = await result.current.isAccessGranted();
    });

    expect(hasAccess).toBe(true);
  });

  it('should deny access to unauthenticated user', async () => {
    supertokensConfig.validateSession.mockResolvedValue(false);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    let hasAccess;
    await act(async () => {
      hasAccess = await result.current.isAccessGranted(['overview']);
    });

    expect(hasAccess).toBe(false);
  });
});

describe('Authentication Context - Profile Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should detect complete profile', async () => {
    const completeProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Test',
        last_name: 'User',
        user_profile: { company: 'Test Co', job_title: 'Dev' },
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(completeProfile);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    const isComplete = result.current.isProfileComplete(result.current.user);
    expect(isComplete).toBe(true);
  });

  it('should update profile successfully', async () => {
    const updatedProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Updated',
        last_name: 'User',
        user_profile: { company: 'New Co', job_title: 'Senior Dev' },
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(updatedProfile);
    apiService.updateProfile.mockResolvedValue(updatedProfile);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    let updateResult;
    await act(async () => {
      updateResult = await result.current.updateProfile({
        email: 'test@example.com',
        first_name: 'Updated',
        last_name: 'User',
        company: 'New Co',
        job_title: 'Senior Dev',
      });
    });

    expect(updateResult.success).toBe(true);
  });
});
