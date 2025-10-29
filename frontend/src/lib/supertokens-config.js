import SuperTokens from "supertokens-web-js";
import Session from "supertokens-web-js/recipe/session";
import Passwordless from "supertokens-web-js/recipe/passwordless";
import { SUPERTOKENS_CONFIG } from "./constants.js";

// Initialize SuperTokens
SuperTokens.init({
  appInfo: {
    appName: SUPERTOKENS_CONFIG.APP_NAME,
    apiDomain: SUPERTOKENS_CONFIG.API_DOMAIN,
    apiBasePath: SUPERTOKENS_CONFIG.API_BASE_PATH,
    websiteDomain: SUPERTOKENS_CONFIG.WEBSITE_DOMAIN,
    websiteBasePath: SUPERTOKENS_CONFIG.WEBSITE_BASE_PATH,
  },
  recipeList: [
    Session.init({
      tokenTransferMethod: "header",
      sessionScope: SUPERTOKENS_CONFIG.SESSION_SCOPE,
      onHandleEvent: (context) => {
        if (context.action === "SIGN_OUT") {
          // Clear any additional local storage or state if needed
          console.log("User signed out");
        } else if (context.action === "SESSION_CREATED") {
          console.log("Session created");
        } else if (context.action === "REFRESH_SESSION") {
          console.log("Session refreshed");
        }
      },
    }),
    Passwordless.init({
      contactMethod: "EMAIL",
      onHandleEvent: (context) => {
        if (context.action === "PASSWORDLESS_CODE_SENT") {
          console.log("OTP sent to email");
        } else if (context.action === "PASSWORDLESS_RESTART_FLOW") {
          console.log("Passwordless flow restarted");
        }
      },
    }),
  ],
});

// Export authentication functions for application-wide usage

/**
 * Send OTP code to the provided email address
 * @param {string} email - User's email address
 * @returns {Promise<{status: string, deviceId?: string, preAuthSessionId?: string}>}
 */
export const sendPasswordlessCode = async (email) => {
  try {
    const response = await Passwordless.createCode({
      email,
    });
    return response;
  } catch (error) {
    console.error("Error sending OTP:", error);
    throw error;
  }
};

/**
 * Verify OTP code and create session
 * @param {string} userInputCode - OTP code entered by user
 * @returns {Promise<{status: string, user?: object}>}
 */
export const consumePasswordlessCode = async (userInputCode) => {
  try {
    const response = await Passwordless.consumeCode({
      userInputCode,
    });
    return response;
  } catch (error) {
    console.error("Error verifying OTP:", error);
    throw error;
  }
};

/**
 * Resend OTP code to the same email
 * @returns {Promise<{status: string}>}
 */
export const resendPasswordlessCode = async () => {
  try {
    const response = await Passwordless.resendCode();
    return response;
  } catch (error) {
    console.error("Error resending OTP:", error);
    throw error;
  }
};

/**
 * Check if a valid session exists
 * @returns {Promise<boolean>}
 */
export const doesSessionExist = async () => {
  try {
    return await Session.doesSessionExist();
  } catch (error) {
    console.error("Error checking session:", error);
    return false;
  }
};

/**
 * Sign out the current user and clear session
 * @returns {Promise<{status: string}>}
 */
export const signOut = async () => {
  try {
    const response = await Session.signOut();
    return response;
  } catch (error) {
    console.error("Error signing out:", error);
    throw error;
  }
};

/**
 * Get the current session's access token
 * @returns {Promise<string|undefined>}
 */
export const getAccessToken = async () => {
  try {
    return await Session.getAccessToken();
  } catch (error) {
    console.error("Error getting access token:", error);
    return undefined;
  }
};

/**
 * Get the current user's ID
 * @returns {Promise<string|undefined>}
 */
export const getUserId = async () => {
  try {
    return await Session.getUserId();
  } catch (error) {
    console.error("Error getting user ID:", error);
    return undefined;
  }
};

/**
 * Get the current user's email from session payload
 * @returns {Promise<string|undefined>}
 */
export const getUserEmail = async () => {
  try {
    // Try to get from access token payload first
    const payload = await Session.getAccessTokenPayloadSecurely();
    
    // SuperTokens passwordless stores email/phone in different fields
    if (payload?.email) return payload.email;
    if (payload?.phoneNumber) return payload.phoneNumber;
    
    // Try to get from Passwordless recipe
    const Passwordless = (await import("supertokens-web-js/recipe/passwordless")).default;
    const loginAttemptInfo = await Passwordless.getLoginAttemptInfo();
    
    if (loginAttemptInfo?.email) return loginAttemptInfo.email;
    if (loginAttemptInfo?.phoneNumber) return loginAttemptInfo.phoneNumber;
    
    return undefined;
  } catch (error) {
    console.error("Error getting user email:", error);
    return undefined;
  }
};

/**
 * Get a specific claim value from the session
 * @param {object} claim - The claim to retrieve
 * @returns {Promise<any>}
 */
export const getClaimValue = async (claim) => {
  try {
    return await Session.getClaimValue(claim);
  } catch (error) {
    console.error("Error getting claim value:", error);
    return undefined;
  }
};

/**
 * Validate current session and refresh if needed
 * @returns {Promise<boolean>}
 */
export const validateSession = async () => {
  try {
    const sessionExists = await Session.doesSessionExist();
    
    // SuperTokens uses cookies for session management
    // If session exists, it's valid - no need to check for access token
    return sessionExists;
  } catch (error) {
    console.error("Error validating session:", error);
    return false;
  }
};

// Export SuperTokens instance for advanced usage
export default SuperTokens;