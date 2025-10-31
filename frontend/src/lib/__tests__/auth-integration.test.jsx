import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../auth-context.jsx';
import * as supertokensConfig from '../supertokens-config.js';
import apiService from '../api-service.js';

// Mock SuperTokens and API service
vi.mock('../supertokens-config.js');
vi.mock('../api-service.js');

describe('Authentication Integration - Complete Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should complete new user registration flow: email → OTP → profile → authenticated', async () => {
    // Step 1: Initial state - no session
    supertokensConfig.validateSession.mockResolvedValue(false);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    expect(result.current.isAuthenticated).toBe(false);

    // Step 2: Send OTP
    supertokensConfig.sendPasswordlessCode.mockResolvedValue({
      status: 'OK',
      deviceId: 'device-123',
      preAuthSessionId: 'session-123',
    });

    let sendResult;
    await act(async () => {
      sendResult = await result.current.sendOTP('newuser@example.com');
    });

    expect(sendResult.success).toBe(true);

    // Step 3: Verify OTP - new user (no profile exists)
    supertokensConfig.consumePasswordlessCode.mockResolvedValue({ status: 'OK' });
    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('new-user-123');
    apiService.getProfile.mockRejectedValue(new Error('Profile not found'));

    let verifyResult;
    await act(async () => {
      verifyResult = await result.current.verifyOTP('123456');
    });

    expect(verifyResult.isNewUser).toBe(true);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.isProfileComplete(result.current.user)).toBe(false);

    // Step 4: Complete profile
    const completeProfile = {
      user_id: 'new-user-123',
      email: 'newuser@example.com',
      metadata: {
        first_name: 'New',
        last_name: 'User',
        user_profile: {
          company: 'Test Company',
          job_title: 'Developer',
        },
      },
    };

    apiService.updateProfile.mockResolvedValue(completeProfile);

    let updateResult;
    await act(async () => {
      updateResult = await result.current.updateProfile({
        email: 'newuser@example.com',
        first_name: 'New',
        last_name: 'User',
        company: 'Test Company',
        job_title: 'Developer',
      });
    });

    expect(updateResult.success).toBe(true);
    expect(result.current.isProfileComplete(result.current.user)).toBe(true);
    expect(result.current.user.metadata.first_name).toBe('New');
  });

  it('should complete returning user flow: email → OTP → authenticated', async () => {
    // Step 1: Initial state - no session
    supertokensConfig.validateSession.mockResolvedValue(false);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    // Step 2: Send OTP
    supertokensConfig.sendPasswordlessCode.mockResolvedValue({
      status: 'OK',
      deviceId: 'device-456',
      preAuthSessionId: 'session-456',
    });

    await act(async () => {
      await result.current.sendOTP('returning@example.com');
    });

    // Step 3: Verify OTP - returning user (profile exists)
    const existingProfile = {
      user_id: 'returning-user-123',
      email: 'returning@example.com',
      metadata: {
        first_name: 'Returning',
        last_name: 'User',
        user_profile: {
          company: 'Existing Company',
          job_title: 'Senior Developer',
        },
      },
    };

    supertokensConfig.consumePasswordlessCode.mockResolvedValue({ status: 'OK' });
    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('returning-user-123');
    apiService.getProfile.mockResolvedValue(existingProfile);

    let verifyResult;
    await act(async () => {
      verifyResult = await result.current.verifyOTP('654321');
    });

    expect(verifyResult.isNewUser).toBe(false);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.isProfileComplete(result.current.user)).toBe(true);
    expect(result.current.user.email).toBe('returning@example.com');
  });
});

describe('Authentication Integration - Error Scenarios', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    supertokensConfig.validateSession.mockResolvedValue(false);
  });

  it('should handle OTP send failure', async () => {
    supertokensConfig.sendPasswordlessCode.mockRejectedValue(
      new Error('Network error')
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    await act(async () => {
      await expect(result.current.sendOTP('test@example.com')).rejects.toThrow();
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should handle OTP verification failure', async () => {
    supertokensConfig.consumePasswordlessCode.mockResolvedValue({
      status: 'INCORRECT_USER_INPUT_CODE_ERROR',
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    await act(async () => {
      await expect(result.current.verifyOTP('wrong-code')).rejects.toThrow();
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should handle profile update failure', async () => {
    const mockProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Test',
        last_name: 'User',
        user_profile: {
          company: 'Test Co',
          job_title: 'Dev',
        },
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(mockProfile);
    apiService.updateProfile.mockRejectedValue(new Error('Update failed'));

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    await act(async () => {
      await expect(
        result.current.updateProfile({
          first_name: 'Updated',
          last_name: 'User',
          company: 'New Co',
          job_title: 'Senior Dev',
        })
      ).rejects.toThrow();
    });

    expect(result.current.error).toBeTruthy();
  });
});

describe('Authentication Integration - Permission-Based Access', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should grant access to authenticated user with complete profile', async () => {
    const mockProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Test',
        last_name: 'User',
        user_profile: {
          company: 'Test Co',
          job_title: 'Dev',
        },
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(mockProfile);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    // Check basic permissions
    let hasOverviewAccess;
    await act(async () => {
      hasOverviewAccess = await result.current.isAccessGranted(['overview']);
    });

    expect(hasOverviewAccess).toBe(true);

    // Check route access
    let canAccessOverview;
    await act(async () => {
      canAccessOverview = await result.current.canAccessRoute('overview');
    });

    expect(canAccessOverview).toBe(true);
  });

  it('should restrict access for incomplete profile', async () => {
    const incompleteProfile = {
      user_id: 'user-123',
      email: 'test@example.com',
      metadata: {
        first_name: 'Test',
      },
    };

    supertokensConfig.validateSession.mockResolvedValue(true);
    supertokensConfig.getUserId.mockResolvedValue('user-123');
    apiService.getProfile.mockResolvedValue(incompleteProfile);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

    expect(result.current.isProfileComplete(result.current.user)).toBe(false);

    // Should only allow access to profile completion route
    let canAccessOverview;
    await act(async () => {
      canAccessOverview = await result.current.canAccessRoute('overview');
    });

    expect(canAccessOverview).toBe(false);

    let canAccessProfileCompletion;
    await act(async () => {
      canAccessProfileCompletion = await result.current.canAccessRoute('complete-profile');
    });

    expect(canAccessProfileCompletion).toBe(true);
  });
});
