import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useCallback,
} from "react";
import {
  sendPasswordlessCode,
  consumePasswordlessCode,
  resendPasswordlessCode,
  signOut as supertokensSignOut,
  getUserId,
  validateSession,
} from "./supertokens-config.js";
import { OTP_CONFIG } from "./constants.js";
import apiService from "./api-service.js";

// Define the AuthUser interface structure
const createAuthUser = (userData = {}) => ({
  user_id: userData.user_id || "",
  email: userData.email || "",
  metadata: {
    first_name: userData.metadata?.first_name || "",
    last_name: userData.metadata?.last_name || "",
    user_profile: {
      company: userData.metadata?.user_profile?.company || "",
      job_title: userData.metadata?.user_profile?.job_title || "",
    },
    user_token: {
      remaining_tokens: userData.metadata?.user_token?.remaining_tokens || 0,
    },
    ...userData.metadata,
  },
});

// Authentication context state structure
const initialState = {
  isAuthenticated: false,
  user: null,
  loading: true,
  otpLoading: false,
  verifyLoading: false,
  profileLoading: false,
  signOutLoading: false,
  isPilotUser: false,
  accessMap: {},
  error: null,
  otpResendCooldown: 0,
  otpAttempts: 0,
};

// Action types for the reducer
const AUTH_ACTIONS = {
  SET_LOADING: "SET_LOADING",
  SET_OTP_LOADING: "SET_OTP_LOADING",
  SET_VERIFY_LOADING: "SET_VERIFY_LOADING",
  SET_PROFILE_LOADING: "SET_PROFILE_LOADING",
  SET_SIGNOUT_LOADING: "SET_SIGNOUT_LOADING",
  SET_AUTHENTICATED: "SET_AUTHENTICATED",
  SET_USER: "SET_USER",
  SET_ERROR: "SET_ERROR",
  CLEAR_ERROR: "CLEAR_ERROR",
  SET_PILOT_STATUS: "SET_PILOT_STATUS",
  SET_ACCESS_MAP: "SET_ACCESS_MAP",
  SET_OTP_COOLDOWN: "SET_OTP_COOLDOWN",
  INCREMENT_OTP_ATTEMPTS: "INCREMENT_OTP_ATTEMPTS",
  RESET_OTP_ATTEMPTS: "RESET_OTP_ATTEMPTS",
  SIGN_OUT: "SIGN_OUT",
};

// Reducer function for managing authentication state
const authReducer = (state, action) => {
  switch (action.type) {
    case AUTH_ACTIONS.SET_LOADING:
      return { ...state, loading: action.payload };
    case AUTH_ACTIONS.SET_OTP_LOADING:
      return { ...state, otpLoading: action.payload };
    case AUTH_ACTIONS.SET_VERIFY_LOADING:
      return { ...state, verifyLoading: action.payload };
    case AUTH_ACTIONS.SET_PROFILE_LOADING:
      return { ...state, profileLoading: action.payload };
    case AUTH_ACTIONS.SET_SIGNOUT_LOADING:
      return { ...state, signOutLoading: action.payload };
    case AUTH_ACTIONS.SET_AUTHENTICATED:
      return { ...state, isAuthenticated: action.payload };
    case AUTH_ACTIONS.SET_USER:
      return { ...state, user: action.payload };
    case AUTH_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload };
    case AUTH_ACTIONS.CLEAR_ERROR:
      return { ...state, error: null };
    case AUTH_ACTIONS.SET_PILOT_STATUS:
      return { ...state, isPilotUser: action.payload };
    case AUTH_ACTIONS.SET_ACCESS_MAP:
      return { ...state, accessMap: action.payload };
    case AUTH_ACTIONS.SET_OTP_COOLDOWN:
      return { ...state, otpResendCooldown: action.payload };
    case AUTH_ACTIONS.INCREMENT_OTP_ATTEMPTS:
      return { ...state, otpAttempts: state.otpAttempts + 1 };
    case AUTH_ACTIONS.RESET_OTP_ATTEMPTS:
      return { ...state, otpAttempts: 0 };
    case AUTH_ACTIONS.SIGN_OUT:
      return {
        ...initialState,
        loading: false,
      };
    default:
      return state;
  }
};

// Create the authentication context
const AuthContext = createContext(null);

// AuthProvider component
export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Get user profile from backend
  const getUserProfile = useCallback(async () => {
    try {
      const sessionExists = await validateSession();
      if (!sessionExists) {
        return null;
      }

      const userId = await getUserId();
      if (!userId) {
        return null;
      }

      const profile = await apiService.getProfile(userId);
      return createAuthUser(profile);
    } catch (error) {
      console.error("Error fetching user profile:", error);
      return null;
    }
  }, []);

  // Check if user has pilot role
  const checkPilotStatus = useCallback(async () => {
    try {
      // This would typically check SuperTokens claims for pilot role
      // For now, we'll implement a basic check
      const sessionExists = await validateSession();
      if (!sessionExists) {
        return false;
      }

      // Check for pilot role claim (this would be configured in SuperTokens backend)
      // For now, we'll return false as a placeholder
      return false;
    } catch (error) {
      console.error("Error checking pilot status:", error);
      return false;
    }
  }, []);

  // Generate access control mapping for navigation permissions
  const generateAccessMap = useCallback(
    async (user) => {
      try {
        if (!user) {
          return {};
        }

        // Basic access mapping - this would be expanded based on actual permissions
        const baseAccess = {
          overview: true,
          requirements: true,
          documents: true,
          integrations: false, // Placeholder for future implementation
          team: false, // Placeholder for future implementation
        };

        // Add pilot user specific access
        const isPilot = await checkPilotStatus();
        if (isPilot) {
          baseAccess.beta_features = true;
          baseAccess.advanced_analytics = true;
        }

        return baseAccess;
      } catch (error) {
        console.error("Error generating access map:", error);
        return {};
      }
    },
    [checkPilotStatus]
  );

  // Common function to update user profile and access map
  const updateUserState = useCallback(
    async (userProfile) => {
      if (userProfile) {
        dispatch({ type: AUTH_ACTIONS.SET_USER, payload: userProfile });
        dispatch({ type: AUTH_ACTIONS.SET_AUTHENTICATED, payload: true });

        const isPilot = await checkPilotStatus();
        dispatch({ type: AUTH_ACTIONS.SET_PILOT_STATUS, payload: isPilot });

        const accessMap = await generateAccessMap(userProfile);
        dispatch({ type: AUTH_ACTIONS.SET_ACCESS_MAP, payload: accessMap });
      }
    },
    [checkPilotStatus, generateAccessMap]
  );

  // Initialize authentication state on app load
  const initializeAuth = useCallback(async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: true });
      dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });

      const sessionExists = await validateSession();

      if (sessionExists) {
        const userProfile = await getUserProfile();
        if (userProfile) {
          await updateUserState(userProfile);
        } else {
          // Session exists but no user profile - this is a new user
          dispatch({ type: AUTH_ACTIONS.SET_AUTHENTICATED, payload: true });
          
          // Try to get basic user info from SuperTokens
          const userId = await getUserId();
          if (userId) {
            const basicUser = createAuthUser({ user_id: userId });
            dispatch({ type: AUTH_ACTIONS.SET_USER, payload: basicUser });
          }
        }
      } else {
        dispatch({ type: AUTH_ACTIONS.SET_AUTHENTICATED, payload: false });
        dispatch({ type: AUTH_ACTIONS.SET_USER, payload: null });
      }
    } catch (error) {
      console.error("Error initializing auth:", error);
      dispatch({
        type: AUTH_ACTIONS.SET_ERROR,
        payload: "Failed to initialize authentication",
      });
      dispatch({ type: AUTH_ACTIONS.SET_AUTHENTICATED, payload: false });
    } finally {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: false });
    }
  }, [getUserProfile, updateUserState]);

  // Initialize auth on component mount
  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]); // Run only once on mount

  // Auto-refresh user data every 60 seconds
  useEffect(() => {
    if (!state.isAuthenticated) return;

    const refreshInterval = setInterval(async () => {
      try {
        const sessionExists = await validateSession();
        if (sessionExists) {
          const userProfile = await getUserProfile();
          if (userProfile) {
            dispatch({ type: AUTH_ACTIONS.SET_USER, payload: userProfile });
            const accessMap = await generateAccessMap(userProfile);
            dispatch({ type: AUTH_ACTIONS.SET_ACCESS_MAP, payload: accessMap });
          }
        } else {
          dispatch({ type: AUTH_ACTIONS.SIGN_OUT });
        }
      } catch (error) {
        console.error("Error refreshing user data:", error);
      }
    }, 300000); // 5 minutes

    return () => clearInterval(refreshInterval);
  }, [state.isAuthenticated, getUserProfile, generateAccessMap]);

  // OTP resend cooldown timer
  useEffect(() => {
    if (state.otpResendCooldown > 0) {
      const timer = setTimeout(() => {
        dispatch({
          type: AUTH_ACTIONS.SET_OTP_COOLDOWN,
          payload: state.otpResendCooldown - 1,
        });
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [state.otpResendCooldown]);

  // Email validation helper
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Send OTP function with email validation and error handling
  const sendOTP = useCallback(
    async (email) => {
      try {
        dispatch({ type: AUTH_ACTIONS.SET_OTP_LOADING, payload: true });
        dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });

        // Validate email format
        if (!email || !validateEmail(email)) {
          throw new Error("Please enter a valid email address");
        }

        // Check cooldown period
        if (state.otpResendCooldown > 0) {
          throw new Error(
            `Please wait ${state.otpResendCooldown} seconds before requesting another OTP`
          );
        }

        const response = await sendPasswordlessCode(email);

        if (response.status === "OK") {
          // Start cooldown timer
          dispatch({
            type: AUTH_ACTIONS.SET_OTP_COOLDOWN,
            payload: OTP_CONFIG.RESEND_COOLDOWN,
          });
          return {
            success: true,
            deviceId: response.deviceId,
            preAuthSessionId: response.preAuthSessionId,
          };
        } else {
          throw new Error("Failed to send OTP. Please try again.");
        }
      } catch (error) {
        console.error("Error sending OTP:", error);
        let errorMessage = "Failed to send OTP. Please try again.";

        // Handle SuperTokens specific errors
        if (error.message.includes("SIGN_IN_UP_NOT_ALLOWED")) {
          errorMessage = "Registration is not allowed for this email address.";
        } else if (error.message.includes("valid email")) {
          errorMessage = error.message;
        } else if (error.message.includes("wait")) {
          errorMessage = error.message;
        }

        dispatch({ type: AUTH_ACTIONS.SET_ERROR, payload: errorMessage });
        throw new Error(errorMessage);
      } finally {
        dispatch({ type: AUTH_ACTIONS.SET_OTP_LOADING, payload: false });
      }
    },
    [state.otpResendCooldown]
  );

  // Verify OTP with attempt tracking and expiration handling
  const verifyOTP = useCallback(
    async (otp) => {
      try {
        dispatch({ type: AUTH_ACTIONS.SET_VERIFY_LOADING, payload: true });
        dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });

        // Validate OTP format
        if (!otp || otp.length < 4) {
          throw new Error("Please enter a valid OTP code");
        }

        // Check attempt limit
        if (state.otpAttempts >= OTP_CONFIG.MAX_ATTEMPTS) {
          throw new Error(
            "Too many failed attempts. Please request a new OTP."
          );
        }

        const response = await consumePasswordlessCode(otp);

        if (response.status === "OK") {
          // Reset OTP attempts on success
          dispatch({ type: AUTH_ACTIONS.RESET_OTP_ATTEMPTS });

          // Check if this is a new user from SuperTokens
          

          // Wait a moment for the session to be fully established
          await new Promise(resolve => setTimeout(resolve, 500));

          // Get user profile - try multiple times if needed
          let userProfile = null;
          let attempts = 0;
          const maxAttempts = 3;
          
          while (!userProfile && attempts < maxAttempts) {
            try {
              userProfile = await getUserProfile();
              if (userProfile) break;
            } catch (error) {
              console.error(`Profile fetch attempt ${attempts + 1} failed:`, error.message);
            }
            attempts++;
            if (attempts < maxAttempts) {
              await new Promise(resolve => setTimeout(resolve, 500));
            }
          }
          
          if (userProfile) {
            // Profile exists - this is a returning user
            await updateUserState(userProfile);
            return { success: true, isNewUser: false };
          } else {
            // No profile found - this is a new user who needs to complete profile
            dispatch({ type: AUTH_ACTIONS.SET_AUTHENTICATED, payload: true });
            
            // Try to get basic user info from SuperTokens
            const userId = await getUserId();
            if (userId) {
              const basicUser = createAuthUser({ user_id: userId });
              dispatch({ type: AUTH_ACTIONS.SET_USER, payload: basicUser });
            }
            
            return { success: true, isNewUser: true };
          }
        } else {
          // Increment attempt counter
          dispatch({ type: AUTH_ACTIONS.INCREMENT_OTP_ATTEMPTS });
          throw new Error("Invalid OTP code. Please try again.");
        }
      } catch (error) {
        console.error("Error verifying OTP:", error);
        let errorMessage = "Invalid OTP code. Please try again.";

        // Handle SuperTokens specific errors
        if (error.message.includes("INCORRECT_USER_INPUT_CODE_ERROR")) {
          dispatch({ type: AUTH_ACTIONS.INCREMENT_OTP_ATTEMPTS });
          const remainingAttempts =
            OTP_CONFIG.MAX_ATTEMPTS - (state.otpAttempts + 1);
          errorMessage = `Invalid OTP code. ${remainingAttempts} attempts remaining.`;
        } else if (error.message.includes("EXPIRED_USER_INPUT_CODE_ERROR")) {
          errorMessage = "OTP code has expired. Please request a new one.";
        } else if (error.message.includes("RESTART_FLOW_ERROR")) {
          errorMessage =
            "Session expired. Please start the login process again.";
        } else if (error.message.includes("Too many failed attempts")) {
          errorMessage = error.message;
        } else if (error.message.includes("valid OTP")) {
          errorMessage = error.message;
        }

        dispatch({ type: AUTH_ACTIONS.SET_ERROR, payload: errorMessage });
        throw new Error(errorMessage);
      } finally {
        dispatch({ type: AUTH_ACTIONS.SET_VERIFY_LOADING, payload: false });
      }
    },
    [state.otpAttempts, getUserProfile, updateUserState]
  );

  // Resend OTP functionality with cooldown timer
  const resendOTP = useCallback(async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_OTP_LOADING, payload: true });
      dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });

      // Check cooldown period
      if (state.otpResendCooldown > 0) {
        throw new Error(
          `Please wait ${state.otpResendCooldown} seconds before requesting another OTP`
        );
      }

      const response = await resendPasswordlessCode();

      if (response.status === "OK") {
        // Start cooldown timer
        dispatch({
          type: AUTH_ACTIONS.SET_OTP_COOLDOWN,
          payload: OTP_CONFIG.RESEND_COOLDOWN,
        });
        // Reset attempt counter on resend
        dispatch({ type: AUTH_ACTIONS.RESET_OTP_ATTEMPTS });
        return { success: true };
      } else {
        throw new Error("Failed to resend OTP. Please try again.");
      }
    } catch (error) {
      console.error("Error resending OTP:", error);
      let errorMessage = "Failed to resend OTP. Please try again.";

      if (error.message.includes("wait")) {
        errorMessage = error.message;
      } else if (error.message.includes("RESTART_FLOW_ERROR")) {
        errorMessage = "Session expired. Please start the login process again.";
      }

      dispatch({ type: AUTH_ACTIONS.SET_ERROR, payload: errorMessage });
      throw new Error(errorMessage);
    } finally {
      dispatch({ type: AUTH_ACTIONS.SET_OTP_LOADING, payload: false });
    }
  }, [state.otpResendCooldown]);

  // Update user profile
  const updateProfile = useCallback(
    async (profileData) => {
      try {
        dispatch({ type: AUTH_ACTIONS.SET_PROFILE_LOADING, payload: true });
        dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });

        // Validate required fields
        const requiredFields = [
          "first_name",
          "last_name",
          "company",
          "job_title",
        ];
        for (const field of requiredFields) {
          if (!profileData[field] || profileData[field].trim() === "") {
            throw new Error(`${field.replace("_", " ")} is required`);
          }
        }

        const userId = await getUserId();
        if (!userId) {
          throw new Error("User ID not found. Please log in again.");
        }

        // Update profile via API (includes email for new user creation)
        const updatedProfile = await apiService.updateProfile(userId, {
          email: profileData.email,
          metadata: {
            first_name: profileData.first_name,
            last_name: profileData.last_name,
            user_profile: {
              company: profileData.company,
              job_title: profileData.job_title,
            },
          },
        });

        // Update local state with new profile data
        const userProfile = createAuthUser(updatedProfile);
        dispatch({ type: AUTH_ACTIONS.SET_USER, payload: userProfile });

        // Refresh access map with updated profile
        const accessMap = await generateAccessMap(userProfile);
        dispatch({ type: AUTH_ACTIONS.SET_ACCESS_MAP, payload: accessMap });

        return { success: true, user: userProfile };
      } catch (error) {
        console.error("Error updating profile:", error);
        let errorMessage = "Failed to update profile. Please try again.";

        if (error.message.includes("required")) {
          errorMessage = error.message;
        } else if (error.message.includes("Session expired")) {
          errorMessage = error.message;
        } else if (error.message.includes("User ID not found")) {
          errorMessage = error.message;
        }

        dispatch({ type: AUTH_ACTIONS.SET_ERROR, payload: errorMessage });
        throw new Error(errorMessage);
      } finally {
        dispatch({ type: AUTH_ACTIONS.SET_PROFILE_LOADING, payload: false });
      }
    },
    [generateAccessMap]
  );

  // Refresh user data manually
  const refreshUser = useCallback(async () => {
    try {
      const sessionExists = await validateSession();
      if (!sessionExists) {
        dispatch({ type: AUTH_ACTIONS.SIGN_OUT });
        return { success: false, reason: "session_expired" };
      }

      const userProfile = await getUserProfile();
      if (userProfile) {
        await updateUserState(userProfile);
        return { success: true, user: userProfile };
      } else {
        // No profile found - sign out
        await supertokensSignOut();
        dispatch({ type: AUTH_ACTIONS.SIGN_OUT });
        return { success: false, reason: "no_profile" };
      }
    } catch (error) {
      console.error("Error refreshing user:", error);
      return { success: false, reason: "error", error: error.message };
    }
  }, [getUserProfile, updateUserState]);

  // Check if user profile is complete
  const isProfileComplete = useCallback((user) => {
    if (!user || !user.metadata) return false;

    const { first_name, last_name, user_profile } = user.metadata;
    return !!(
      first_name &&
      last_name &&
      user_profile?.company &&
      user_profile?.job_title
    );
  }, []);

  // Secure sign-out functionality
  const signOut = useCallback(async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_SIGNOUT_LOADING, payload: true });
      dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });

      // Attempt to sign out from SuperTokens
      try {
        await supertokensSignOut();
      } catch (error) {
        // Even if SuperTokens sign out fails, we should clear local state
        console.warn(
          "SuperTokens sign out failed, but clearing local state:",
          error
        );
      }

      // Clear all local authentication state
      dispatch({ type: AUTH_ACTIONS.SIGN_OUT });

      return { success: true };
    } catch (error) {
      console.error("Error during sign out:", error);
      // Even on error, clear local state for security
      dispatch({ type: AUTH_ACTIONS.SIGN_OUT });
      return { success: true }; // Always return success for sign out
    } finally {
      dispatch({ type: AUTH_ACTIONS.SET_SIGNOUT_LOADING, payload: false });
    }
  }, []);

  // Enhanced session validation with automatic refresh
  const validateAndRefreshSession = useCallback(async () => {
    try {
      const sessionExists = await validateSession();
      if (!sessionExists) {
        dispatch({ type: AUTH_ACTIONS.SIGN_OUT });
        return false;
      }

      // If session exists but user data is stale, refresh it
      if (state.isAuthenticated && state.user) {
        const refreshResult = await refreshUser();
        return refreshResult.success;
      }

      return true;
    } catch (error) {
      console.error("Error validating session:", error);
      dispatch({ type: AUTH_ACTIONS.SIGN_OUT });
      return false;
    }
  }, [state.isAuthenticated, state.user, refreshUser]);

  // Check if user has admin role (placeholder)
  const checkAdminRole = useCallback(async () => {
    return false;
  }, []);

  // Check custom role via SuperTokens claims
  const checkCustomRole = useCallback(async () => {
    return false;
  }, []);

  // Check specific permission claim (placeholder for SuperTokens integration)
  const checkPermissionClaim = useCallback(
    async (permission) => {
      try {
        // This would use SuperTokens getClaimValue with specific permission claims
        // For now, we'll implement basic permission checking

        // Basic permissions that all authenticated users have
        const basicPermissions = ["overview", "requirements", "documents"];
        if (basicPermissions.includes(permission)) {
          return true;
        }

        // Pilot user permissions
        if (state.isPilotUser) {
          const pilotPermissions = [
            "beta_features",
            "advanced_analytics",
            "integrations",
          ];
          if (pilotPermissions.includes(permission)) {
            return true;
          }
        }

        // Admin permissions (placeholder)
        const isAdmin = await checkAdminRole();
        if (isAdmin) {
          const adminPermissions = ["team", "admin_panel", "user_management"];
          if (adminPermissions.includes(permission)) {
            return true;
          }
        }

        return false;
      } catch (error) {
        console.error("Error checking permission claim:", error);
        return false;
      }
    },
    [state.isPilotUser, checkAdminRole]
  );

  // Permission validation using SuperTokens claims and local access map
  const isAccessGranted = useCallback(
    async (permissions = []) => {
      try {
        // If not authenticated, deny access
        if (!state.isAuthenticated || !state.user) {
          return false;
        }

        // If no specific permissions required, grant access to authenticated users
        if (!permissions || permissions.length === 0) {
          return true;
        }

        // Check each permission against access map
        for (const permission of permissions) {
          // Check local access map first (for performance)
          if (state.accessMap[permission] === true) {
            continue; // This permission is granted
          } else if (state.accessMap[permission] === false) {
            return false; // This permission is explicitly denied
          }

          // If not in access map, check SuperTokens claims
          try {
            // This would check specific claims from SuperTokens
            // For now, we'll use basic role checking
            const sessionExists = await validateSession();
            if (!sessionExists) {
              return false;
            }

            // Check for specific permission claims
            // This would be expanded based on actual SuperTokens claim structure
            const hasPermission = await checkPermissionClaim(permission);
            if (!hasPermission) {
              return false;
            }
          } catch (error) {
            console.error(`Error checking permission ${permission}:`, error);
            return false;
          }
        }

        return true;
      } catch (error) {
        console.error("Error validating access:", error);
        return false;
      }
    },
    [state.isAuthenticated, state.user, state.accessMap, checkPermissionClaim]
  );

  // Role checking for pilot users and other roles
  const hasRole = useCallback(
    async (role) => {
      try {
        if (!state.isAuthenticated || !state.user) {
          return false;
        }

        switch (role) {
          case "pilot":
            return state.isPilotUser;
          case "admin":
            return await checkAdminRole();
          case "user":
            return true; // All authenticated users have 'user' role
          default:
            // Check custom roles via SuperTokens claims
            return await checkCustomRole();
        }
      } catch (error) {
        console.error(`Error checking role ${role}:`, error);
        return false;
      }
    },
    [
      state.isAuthenticated,
      state.user,
      state.isPilotUser,
      checkAdminRole,
      checkCustomRole,
    ]
  );

  // Refresh access mapping functionality
  const refreshAccessMap = useCallback(async () => {
    try {
      if (!state.user) {
        dispatch({ type: AUTH_ACTIONS.SET_ACCESS_MAP, payload: {} });
        return {};
      }

      const newAccessMap = await generateAccessMap(state.user);
      dispatch({ type: AUTH_ACTIONS.SET_ACCESS_MAP, payload: newAccessMap });
      return newAccessMap;
    } catch (error) {
      console.error("Error refreshing access map:", error);
      return state.accessMap;
    }
  }, [state.user, generateAccessMap, state.accessMap]);

  // Navigation-based permission checking
  const canAccessRoute = useCallback(
    async (routeName) => {
      try {
        // Public routes that don't require authentication
        const publicRoutes = ["login", "signup", "forgot-password"];
        if (publicRoutes.includes(routeName)) {
          return true;
        }

        // Check if user is authenticated
        if (!state.isAuthenticated) {
          return false;
        }

        // Check if profile is complete for protected routes
        if (!isProfileComplete(state.user)) {
          // Only allow access to profile completion route
          return routeName === "complete-profile";
        }

        // Check specific route permissions
        const routePermissions = {
          overview: ["overview"],
          requirements: ["requirements"],
          documents: ["documents"],
          integrations: ["integrations"],
          team: ["team"],
          admin: ["admin_panel"],
          beta: ["beta_features"],
        };

        const requiredPermissions = routePermissions[routeName];
        if (requiredPermissions) {
          return await isAccessGranted(requiredPermissions);
        }

        // Default to allowing access for authenticated users with complete profiles
        return true;
      } catch (error) {
        console.error(`Error checking route access for ${routeName}:`, error);
        return false;
      }
    },
    [state.isAuthenticated, state.user, isProfileComplete, isAccessGranted]
  );

  // Health check integration for backend services
  const checkBackendHealth = useCallback(async () => {
    try {
      const healthStatus = await apiService.authenticatedHealthCheckAll();
      return healthStatus;
    } catch (error) {
      console.error("Error checking backend health:", error);
      return {
        core: { status: "error", error: error.message },
        ai: { status: "error", error: error.message },
      };
    }
  }, []);

  // Get profile completion status
  const getProfileCompletionStatus = useCallback(async () => {
    try {
      if (!state.user?.user_id) {
        return { isComplete: false, missingFields: ["user_id"] };
      }

      return await apiService.getProfileCompletionStatus(state.user.user_id);
    } catch (error) {
      console.error("Error getting profile completion status:", error);
      return { isComplete: false, error: error.message };
    }
  }, [state.user?.user_id]);

  // Context value object
  const contextValue = {
    // State
    isAuthenticated: state.isAuthenticated,
    user: state.user,
    loading: state.loading,
    otpLoading: state.otpLoading,
    verifyLoading: state.verifyLoading,
    profileLoading: state.profileLoading,
    signOutLoading: state.signOutLoading,
    isPilotUser: state.isPilotUser,
    accessMap: state.accessMap,
    error: state.error,
    otpResendCooldown: state.otpResendCooldown,
    otpAttempts: state.otpAttempts,

    // OTP Authentication Methods
    sendOTP,
    verifyOTP,
    resendOTP,

    // Session Management and Profile Methods
    updateProfile,
    signOut,
    refreshUser,
    isProfileComplete,
    validateAndRefreshSession,
    getProfileCompletionStatus,

    // Role-Based Access Control Methods
    isAccessGranted,
    hasRole,
    canAccessRoute,
    refreshAccessMap,

    // Backend Integration Methods
    checkBackendHealth,

    // Utility Methods
    clearError: useCallback(() => dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR }), []),
  };

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
};

// Custom hook to use the auth context
// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;
