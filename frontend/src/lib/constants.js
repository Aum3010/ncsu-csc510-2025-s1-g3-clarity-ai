// SuperTokens and API configuration constants

export const SUPERTOKENS_CONFIG = {
  APP_NAME: "Krexin Frontend",
  API_DOMAIN: import.meta.env.VITE_API_DOMAIN || "http://localhost:5000",
  WEBSITE_DOMAIN: import.meta.env.VITE_WEBSITE_DOMAIN || "http://localhost:5173",
  SESSION_SCOPE: import.meta.env.VITE_SESSION_SCOPE || "localhost",
  API_BASE_PATH: "/auth",
  WEBSITE_BASE_PATH: "/auth",
};

export const API_ENDPOINTS = {
  CORE_API: SUPERTOKENS_CONFIG.API_DOMAIN,
  AUTH_API: `${SUPERTOKENS_CONFIG.API_DOMAIN}${SUPERTOKENS_CONFIG.API_BASE_PATH}`,
};

export const ROUTES = {
  LOGIN: "/login",
  DASHBOARD: "/dashboard",
  PROFILE_COMPLETION: "/complete-profile",
};

export const OTP_CONFIG = {
  RESEND_COOLDOWN: 60, // seconds
  MAX_ATTEMPTS: 5,
};