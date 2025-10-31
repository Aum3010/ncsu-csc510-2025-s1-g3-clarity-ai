import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../lib/auth-context.jsx";
import Notification from "../components/Notification.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import CountdownTimer from "../components/CountdownTimer.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";

// Login step constants
const LOGIN_STEPS = {
  EMAIL: "email",
  OTP: "otp",
  PROFILE: "profile",
};

const LoginPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    isAuthenticated,
    user,
    loading,
    otpLoading,
    verifyLoading,
    profileLoading,
    error,
    otpResendCooldown,
    otpAttempts,
    sendOTP,
    verifyOTP,
    resendOTP,
    updateProfile,
    signOut,
    signOutLoading,
    isProfileComplete,
    clearError,
  } = useAuth();

  // Get current step from URL params or default to email
  const [currentStep, setCurrentStep] = useState(
    searchParams.get("step") || LOGIN_STEPS.EMAIL
  );
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [profileData, setProfileData] = useState({
    first_name: "",
    last_name: "",
    company: "",
    job_title: "",
  });
  const [successMessage, setSuccessMessage] = useState("");
  const [showSuccess, setShowSuccess] = useState(false);
  const [showEmailChangeDialog, setShowEmailChangeDialog] = useState(false);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);

  // Update URL when step changes
  useEffect(() => {
    setSearchParams({ step: currentStep });
  }, [currentStep, setSearchParams]);

  // Handle authentication state changes
  useEffect(() => {
    const handleAuthState = async () => {
      if (!loading && isAuthenticated && user) {
        if (isProfileComplete(user)) {
          navigate("/overview", { replace: true });
        } else {
          setCurrentStep(LOGIN_STEPS.PROFILE);
          
          // Get email from localStorage if not already set
          const storedEmail = localStorage.getItem('pendingUserEmail');
          if (storedEmail && !email) {
            setEmail(storedEmail);
          }
        }
      }
    };
    
    handleAuthState();
  }, [loading, isAuthenticated, user, isProfileComplete, navigate, email]);

  // Clear error and success messages when step changes
  useEffect(() => {
    clearError();
    setSuccessMessage("");
    setShowSuccess(false);
  }, [currentStep, clearError]);

  // Show success message helper
  const showSuccessMessage = (message) => {
    setSuccessMessage(message);
    setShowSuccess(true);
  };

  // Handle email submission and OTP sending
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      return;
    }

    try {
      // Store email in localStorage for profile completion
      localStorage.setItem('pendingUserEmail', email);
      
      await sendOTP(email);
      showSuccessMessage("Verification code sent to your email!");
      setCurrentStep(LOGIN_STEPS.OTP);
    } catch (error) {
      // Error is handled by auth context
      console.error("Failed to send OTP:", error);
    }
  };

  // Handle OTP verification
  const handleOtpSubmit = async (e) => {
    e.preventDefault();
    if (!otp.trim()) {
      return;
    }

    try {
      const result = await verifyOTP(otp);
      
      if (result && result.success) {
        if (result.isNewUser) {
          showSuccessMessage("Email verified! Please complete your profile.");
          // Let the auth state useEffect handle the step change automatically
        } else {
          showSuccessMessage("Welcome back! Redirecting to dashboard...");
          // Let the auth state useEffect handle the redirect automatically
        }
      }
    } catch (error) {
      // Error is handled by auth context
      console.error("Failed to verify OTP:", error);
    }
  };

  // Handle profile completion
  const handleProfileSubmit = async (e) => {
    e.preventDefault();

    // Validate all fields using enhanced validation
    const validationErrors = getProfileValidationErrors();

    if (Object.keys(validationErrors).length > 0) {
      // The errors will be shown in the field validation messages
      return;
    }

    try {
      // Include email in profile data for new user creation
      const profileDataWithEmail = {
        ...profileData,
        email: email,
      };
      const result = await updateProfile(profileDataWithEmail);
      
      if (result && result.success) {
        // Clear stored email after successful profile creation
        localStorage.removeItem('pendingUserEmail');
        
        showSuccessMessage("Profile completed successfully! Welcome to Clarity.");
        // Redirect to dashboard after successful profile update
        setTimeout(() => {
          navigate("/overview", { replace: true });
        }, 1000);
      }
    } catch (error) {
      // Error is handled by auth context
      console.error("Failed to update profile:", error);
    }
  };

  // Handle OTP resend
  const handleResendOtp = async () => {
    try {
      await resendOTP();
      showSuccessMessage("New verification code sent to your email!");
    } catch (error) {
      // Error is handled by auth context
      console.error("Failed to resend OTP:", error);
    }
  };

  // Handle email change confirmation
  const handleChangeEmailConfirm = async () => {
    try {
      // Sign out current session to allow email change
      await signOut();
      setCurrentStep(LOGIN_STEPS.EMAIL);
      setEmail("");
      setOtp("");
      setProfileData({
        first_name: "",
        last_name: "",
        company: "",
        job_title: "",
      });
      clearError();
      setShowEmailChangeDialog(false);
      showSuccessMessage(
        "Signed out successfully. You can now use a different email."
      );
    } catch (error) {
      console.error("Error during email change:", error);
      setShowEmailChangeDialog(false);
    }
  };

  // Handle logout confirmation
  const handleLogoutConfirm = async () => {
    try {
      await signOut();
      setCurrentStep(LOGIN_STEPS.EMAIL);
      setEmail("");
      setOtp("");
      setProfileData({
        first_name: "",
        last_name: "",
        company: "",
        job_title: "",
      });
      clearError();
      setShowLogoutDialog(false);
      showSuccessMessage("Signed out successfully.");
    } catch (error) {
      console.error("Error during logout:", error);
      setShowLogoutDialog(false);
    }
  };

  // Show email change dialog
  const handleChangeEmail = () => {
    setShowEmailChangeDialog(true);
  };

  // Show logout dialog
  const handleLogout = () => {
    setShowLogoutDialog(true);
  };

  // Handle profile data changes
  const handleProfileChange = (field, value) => {
    setProfileData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  // Enhanced profile validation
  const validateProfileField = (field, value) => {
    if (!value || value.trim().length === 0) {
      return {
        isValid: false,
        message: `${field.replace("_", " ")} is required`,
      };
    }

    switch (field) {
      case "first_name":
      case "last_name":
        if (value.trim().length < 2) {
          return {
            isValid: false,
            message: `${field.replace("_", " ")} must be at least 2 characters`,
          };
        }
        if (!/^[a-zA-Z\s'-]+$/.test(value)) {
          return {
            isValid: false,
            message: `${field.replace(
              "_",
              " "
            )} can only contain letters, spaces, hyphens, and apostrophes`,
          };
        }
        break;
      case "company":
        if (value.trim().length < 2) {
          return {
            isValid: false,
            message: "Company name must be at least 2 characters",
          };
        }
        break;
      case "job_title":
        if (value.trim().length < 2) {
          return {
            isValid: false,
            message: "Job title must be at least 2 characters",
          };
        }
        break;
    }

    return { isValid: true, message: "" };
  };

  // Get all profile validation errors
  const getProfileValidationErrors = () => {
    const errors = {};
    const fields = ["first_name", "last_name", "company", "job_title"];

    fields.forEach((field) => {
      const validation = validateProfileField(field, profileData[field]);
      if (!validation.isValid) {
        errors[field] = validation.message;
      }
    });

    return errors;
  };

  // Check if profile field is valid
  const isFieldValid = (field) => {
    const validation = validateProfileField(field, profileData[field]);
    return validation.isValid;
  };

  // Get field validation class
  const getFieldValidationClass = (field) => {
    if (!profileData[field]) return "";
    return isFieldValid(field)
      ? "border-green-300 focus:border-green-500 focus:ring-green-500"
      : "border-red-300 focus:border-red-500 focus:ring-red-500";
  };

  // Get field validation message
  const getFieldValidationMessage = (field) => {
    if (!profileData[field]) return "";
    const validation = validateProfileField(field, profileData[field]);
    return validation.isValid ? "" : validation.message;
  };

  // Show loading spinner during initial auth check
  if (loading) {
    return <LoadingSpinner fullScreen text="Checking authentication..." />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {currentStep === LOGIN_STEPS.EMAIL && "Sign in to your account"}
            {currentStep === LOGIN_STEPS.OTP && "Verify your email"}
            {currentStep === LOGIN_STEPS.PROFILE && "Complete your profile"}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {currentStep === LOGIN_STEPS.EMAIL &&
              "Enter your email to receive a verification code"}
            {currentStep === LOGIN_STEPS.OTP && `We sent a code to ${email}`}
            {currentStep === LOGIN_STEPS.PROFILE &&
              "Please provide some additional information"}
          </p>
        </div>

        {/* Success Message */}
        <Notification
          type="success"
          message={successMessage}
          isVisible={showSuccess}
          onClose={() => setShowSuccess(false)}
          autoClose={true}
          duration={4000}
        />

        {/* Error Display */}
        <Notification
          type="error"
          message={error}
          isVisible={!!error}
          onClose={clearError}
          autoClose={false}
        />

        {/* Email Step */}
        {currentStep === LOGIN_STEPS.EMAIL && (
          <form className="mt-8 space-y-6" onSubmit={handleEmailSubmit}>
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={otpLoading}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={otpLoading || !email.trim()}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {otpLoading ? (
                  <>
                    <LoadingSpinner size="sm" color="white" className="mr-2" />
                    Sending code...
                  </>
                ) : (
                  "Send verification code"
                )}
              </button>
            </div>
          </form>
        )}

        {/* OTP Step */}
        {currentStep === LOGIN_STEPS.OTP && (
          <form className="mt-8 space-y-6" onSubmit={handleOtpSubmit}>
            <div>
              <label htmlFor="otp" className="sr-only">
                Verification code
              </label>
              <input
                id="otp"
                name="otp"
                type="text"
                autoComplete="one-time-code"
                required
                maxLength="6"
                className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm text-center text-lg tracking-widest"
                placeholder="Enter 6-digit code"
                value={otp}
                onChange={(e) =>
                  setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
                }
                disabled={verifyLoading}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={verifyLoading || !otp.trim() || otp.length < 4}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {verifyLoading ? (
                  <>
                    <LoadingSpinner size="sm" color="white" className="mr-2" />
                    Verifying...
                  </>
                ) : (
                  "Verify code"
                )}
              </button>
            </div>

            {/* Resend OTP */}
            <div className="text-center">
              {otpResendCooldown > 0 ? (
                <p className="text-sm text-gray-600">
                  Resend code in{" "}
                  <CountdownTimer
                    initialTime={otpResendCooldown}
                    onComplete={() => {}}
                    className="font-medium text-blue-600"
                    suffix=" seconds"
                  />
                </p>
              ) : (
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={otpLoading}
                  className="text-sm text-blue-600 hover:text-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-1"
                >
                  {otpLoading && <LoadingSpinner size="sm" color="blue" />}
                  <span>{otpLoading ? "Sending..." : "Resend code"}</span>
                </button>
              )}
            </div>

            {/* Change Email */}
            <div className="text-center">
              <button
                type="button"
                onClick={handleChangeEmail}
                className="text-sm text-gray-600 hover:text-gray-500"
              >
                Change email address
              </button>
            </div>

            {/* Attempt Counter with Visual Feedback */}
            {otpAttempts > 0 && (
              <div className="text-center">
                <div className="flex items-center justify-center space-x-2">
                  <p className="text-sm text-gray-600">
                    Attempts: {otpAttempts}/5
                  </p>
                  {otpAttempts >= 3 && (
                    <span className="text-xs text-yellow-600 bg-yellow-100 px-2 py-1 rounded-full">
                      {otpAttempts >= 4 ? "Last attempt!" : "Few attempts left"}
                    </span>
                  )}
                </div>
                {/* Visual progress bar for attempts */}
                <div className="mt-2 w-full bg-gray-200 rounded-full h-1">
                  <div
                    className={`h-1 rounded-full transition-all duration-300 ${
                      otpAttempts <= 2
                        ? "bg-green-500"
                        : otpAttempts <= 3
                        ? "bg-yellow-500"
                        : "bg-red-500"
                    }`}
                    style={{ width: `${(otpAttempts / 5) * 100}%` }}
                  ></div>
                </div>
              </div>
            )}
          </form>
        )}

        {/* Profile Completion Step */}
        {currentStep === LOGIN_STEPS.PROFILE && (
          <form className="mt-8 space-y-6" onSubmit={handleProfileSubmit}>
            <div className="space-y-4">
              {/* Email field (readonly, for reference) */}
              <div>
                <label
                  htmlFor="profile_email"
                  className="block text-sm font-medium text-gray-700"
                >
                  Email
                </label>
                <input
                  id="profile_email"
                  name="profile_email"
                  type="email"
                  readOnly
                  className="mt-1 appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 bg-gray-50 focus:outline-none sm:text-sm"
                  value={email}
                  disabled
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="first_name"
                    className="block text-sm font-medium text-gray-700"
                  >
                    First Name *
                  </label>
                  <input
                    id="first_name"
                    name="first_name"
                    type="text"
                    required
                    className={`mt-1 appearance-none rounded-md relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 focus:outline-none focus:z-10 sm:text-sm ${
                      getFieldValidationClass("first_name") ||
                      "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
                    }`}
                    placeholder="First name"
                    value={profileData.first_name}
                    onChange={(e) =>
                      handleProfileChange("first_name", e.target.value)
                    }
                    disabled={profileLoading}
                  />
                  {getFieldValidationMessage("first_name") && (
                    <p className="mt-1 text-sm text-red-600">
                      {getFieldValidationMessage("first_name")}
                    </p>
                  )}
                </div>
                <div>
                  <label
                    htmlFor="last_name"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Last Name *
                  </label>
                  <input
                    id="last_name"
                    name="last_name"
                    type="text"
                    required
                    className={`mt-1 appearance-none rounded-md relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 focus:outline-none focus:z-10 sm:text-sm ${
                      getFieldValidationClass("last_name") ||
                      "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
                    }`}
                    placeholder="Last name"
                    value={profileData.last_name}
                    onChange={(e) =>
                      handleProfileChange("last_name", e.target.value)
                    }
                    disabled={profileLoading}
                  />
                  {getFieldValidationMessage("last_name") && (
                    <p className="mt-1 text-sm text-red-600">
                      {getFieldValidationMessage("last_name")}
                    </p>
                  )}
                </div>
              </div>

              <div>
                <label
                  htmlFor="company"
                  className="block text-sm font-medium text-gray-700"
                >
                  Company *
                </label>
                <input
                  id="company"
                  name="company"
                  type="text"
                  required
                  className={`mt-1 appearance-none rounded-md relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 focus:outline-none focus:z-10 sm:text-sm ${
                    getFieldValidationClass("company") ||
                    "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
                  }`}
                  placeholder="Company name"
                  value={profileData.company}
                  onChange={(e) =>
                    handleProfileChange("company", e.target.value)
                  }
                  disabled={profileLoading}
                />
                {getFieldValidationMessage("company") && (
                  <p className="mt-1 text-sm text-red-600">
                    {getFieldValidationMessage("company")}
                  </p>
                )}
              </div>

              <div>
                <label
                  htmlFor="job_title"
                  className="block text-sm font-medium text-gray-700"
                >
                  Job Title *
                </label>
                <input
                  id="job_title"
                  name="job_title"
                  type="text"
                  required
                  className={`mt-1 appearance-none rounded-md relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 focus:outline-none focus:z-10 sm:text-sm ${
                    getFieldValidationClass("job_title") ||
                    "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
                  }`}
                  placeholder="Job title"
                  value={profileData.job_title}
                  onChange={(e) =>
                    handleProfileChange("job_title", e.target.value)
                  }
                  disabled={profileLoading}
                />
                {getFieldValidationMessage("job_title") && (
                  <p className="mt-1 text-sm text-red-600">
                    {getFieldValidationMessage("job_title")}
                  </p>
                )}
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={
                  profileLoading ||
                  Object.keys(getProfileValidationErrors()).length > 0
                }
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {profileLoading ? (
                  <>
                    <LoadingSpinner size="sm" color="white" className="mr-2" />
                    Completing profile...
                  </>
                ) : (
                  "Complete profile"
                )}
              </button>
            </div>

            {/* Profile Management Options */}
            <div className="flex justify-center space-x-6 text-center">
              <button
                type="button"
                onClick={handleChangeEmail}
                disabled={signOutLoading}
                className="text-sm text-blue-600 hover:text-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {signOutLoading ? "Signing out..." : "Change email address"}
              </button>
              <button
                type="button"
                onClick={handleLogout}
                disabled={signOutLoading}
                className="text-sm text-gray-600 hover:text-gray-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
              >
                {signOutLoading && <LoadingSpinner size="sm" color="gray" />}
                <span>{signOutLoading ? "Signing out..." : "Sign out"}</span>
              </button>
            </div>
          </form>
        )}

        {/* Step Indicator */}
        <div className="flex justify-center space-x-2 mt-8">
          <div
            className={`h-2 w-8 rounded-full ${
              currentStep === LOGIN_STEPS.EMAIL ? "bg-blue-600" : "bg-gray-300"
            }`}
          ></div>
          <div
            className={`h-2 w-8 rounded-full ${
              currentStep === LOGIN_STEPS.OTP ? "bg-blue-600" : "bg-gray-300"
            }`}
          ></div>
          <div
            className={`h-2 w-8 rounded-full ${
              currentStep === LOGIN_STEPS.PROFILE
                ? "bg-blue-600"
                : "bg-gray-300"
            }`}
          ></div>
        </div>
      </div>

      {/* Email Change Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showEmailChangeDialog}
        title="Change Email Address"
        message="This will sign you out and clear your current progress. You'll need to start the authentication process again with a new email address. Are you sure you want to continue?"
        confirmText="Change Email"
        cancelText="Cancel"
        onConfirm={handleChangeEmailConfirm}
        onCancel={() => setShowEmailChangeDialog(false)}
        loading={signOutLoading}
        type="warning"
      />

      {/* Logout Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showLogoutDialog}
        title="Sign Out"
        message="This will sign you out and clear your current progress. You'll need to start the authentication process again. Are you sure you want to sign out?"
        confirmText="Sign Out"
        cancelText="Cancel"
        onConfirm={handleLogoutConfirm}
        onCancel={() => setShowLogoutDialog(false)}
        loading={signOutLoading}
        type="info"
      />
    </div>
  );
};

export default LoginPage;
