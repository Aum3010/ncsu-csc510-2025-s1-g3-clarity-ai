import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth-context.jsx';
import LoadingSpinner from './LoadingSpinner.jsx';

/**
 * SuperTokens Auth Callback Component
 * Handles magic link authentication and redirects
 */
function SuperTokensAuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, loading, isProfileComplete } = useAuth();
  const [authStatus, setAuthStatus] = useState('processing');
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        setAuthStatus('processing');
        
        // SuperTokens will automatically handle the magic link authentication
        // We just need to wait for the auth context to update
        
        // Give SuperTokens a moment to process the authentication
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Check if authentication was successful
        if (isAuthenticated && user) {
          setAuthStatus('success');
          
          // Redirect based on profile completion status
          if (isProfileComplete(user)) {
            navigate('/overview', { replace: true });
          } else {
            navigate('/login?step=profile', { replace: true });
          }
        } else {
          // If still not authenticated after processing, there might be an error
          setAuthStatus('error');
          setError('Authentication failed. Please try again.');
          
          // Redirect back to login after a delay
          setTimeout(() => {
            navigate('/login', { replace: true });
          }, 3000);
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        setAuthStatus('error');
        setError('Authentication failed. Please try again.');
        
        // Redirect back to login after a delay
        setTimeout(() => {
          navigate('/login', { replace: true });
        }, 3000);
      }
    };

    // Only process if we're not already authenticated and not still loading
    if (!loading) {
      handleAuthCallback();
    }
  }, [isAuthenticated, user, loading, isProfileComplete, navigate]);

  // Show loading state while processing
  if (loading || authStatus === 'processing') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner size="xl" />
          <h2 className="mt-4 text-xl font-semibold text-gray-900">
            Signing you in...
          </h2>
          <p className="mt-2 text-gray-600">
            Please wait while we verify your authentication.
          </p>
        </div>
      </div>
    );
  }

  // Show success state briefly before redirect
  if (authStatus === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
            <span className="text-2xl">✅</span>
          </div>
          <h2 className="text-xl font-semibold text-gray-900">
            Authentication Successful!
          </h2>
          <p className="mt-2 text-gray-600">
            Redirecting you to the application...
          </p>
        </div>
      </div>
    );
  }

  // Show error state
  if (authStatus === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
            <span className="text-2xl">❌</span>
          </div>
          <h2 className="text-xl font-semibold text-gray-900">
            Authentication Failed
          </h2>
          <p className="mt-2 text-gray-600">
            {error || 'Something went wrong during authentication.'}
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Redirecting you back to login...
          </p>
        </div>
      </div>
    );
  }

  return null;
}

export default SuperTokensAuthCallback;