import React, { useEffect, useState, useMemo } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth-context.jsx';
import LoadingSpinner from './LoadingSpinner.jsx';

/**
 * AuthWrapper - Flexible route protection component with configurable requirements
 * 
 * This component provides more granular control over route protection compared to AuthGuard.
 * It supports custom validation, partial access, role-based access, and flexible redirect handling.
 * 
 * Usage Examples:
 * 
 * // Basic protection (same as AuthGuard)
 * <AuthWrapper>
 *   <ProtectedComponent />
 * </AuthWrapper>
 * 
 * // Admin-only route with custom redirect
 * <AuthWrapper 
 *   authConfig={{
 *     roles: ['admin'],
 *     redirectTo: '/unauthorized'
 *   }}
 * >
 *   <AdminPanel />
 * </AuthWrapper>
 * 
 * // Route with specific permissions and partial access
 * <AuthWrapper 
 *   authConfig={{
 *     permissions: ['read_documents', 'write_documents'],
 *     allowPartialAccess: true
 *   }}
 *   onAccessDenied={(context) => console.log('Access denied:', context)}
 * >
 *   <DocumentEditor />
 * </AuthWrapper>
 * 
 * // Public route with custom handling
 * <AuthWrapper 
 *   authConfig={{ requireAuth: false }}
 *   onAccessGranted={(context) => console.log('Public access:', context)}
 * >
 *   <PublicContent />
 * </AuthWrapper>
 * 
 * AuthWrapper - Flexible route protection component with configurable requirements
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components to render when access is granted
 * @param {Object} props.authConfig - Authentication configuration object
 * @param {boolean} props.authConfig.requireAuth - Whether authentication is required (default: true)
 * @param {boolean} props.authConfig.requireCompleteProfile - Whether complete profile is required (default: true)
 * @param {boolean} props.authConfig.requirePilot - Whether pilot user status is required (default: false)
 * @param {string[]} props.authConfig.permissions - Required permissions array
 * @param {string[]} props.authConfig.roles - Required roles array (user needs at least one)
 * @param {string} props.authConfig.redirectTo - Custom redirect destination for unauthorized access
 * @param {boolean} props.authConfig.allowPartialAccess - Allow access even if some permissions are missing
 * @param {Function} props.authConfig.customValidator - Custom validation function
 * @param {React.ReactNode} props.fallback - Custom fallback component for unauthorized access
 * @param {React.ReactNode} props.loadingComponent - Custom loading component
 * @param {Function} props.onAccessDenied - Callback when access is denied
 * @param {Function} props.onAccessGranted - Callback when access is granted
 */
const AuthWrapper = ({ 
  children,
  authConfig = {},
  fallback = null,
  loadingComponent = null,
  onAccessDenied = null,
  onAccessGranted = null
}) => {
  const location = useLocation();
  const { 
    isAuthenticated, 
    user, 
    loading, 
    isProfileComplete,
    validateAndRefreshSession,
    isAccessGranted,
    hasRole,
    canAccessRoute,
    isPilotUser
  } = useAuth();

  // Default configuration
  const config = useMemo(() => ({
    requireAuth: true,
    requireCompleteProfile: true,
    requirePilot: false,
    permissions: [],
    roles: [],
    redirectTo: '/login',
    allowPartialAccess: false,
    customValidator: null,
    ...authConfig
  }), [authConfig]);

  const [authValidating, setAuthValidating] = useState(false);
  const [permissionValidating, setPermissionValidating] = useState(false);
  const [accessResult, setAccessResult] = useState({
    hasAccess: null,
    reason: null,
    missingPermissions: [],
    missingRoles: []
  });

  // Enhanced session validation
  useEffect(() => {
    const validateAuth = async () => {
      if (loading) return;
      
      setAuthValidating(true);
      try {
        // For public routes, skip session validation
        if (!config.requireAuth) {
          setAccessResult({
            hasAccess: true,
            reason: 'public_route',
            missingPermissions: [],
            missingRoles: []
          });
          return;
        }

        // Validate and refresh session
        const sessionValid = await validateAndRefreshSession();
        
        if (!sessionValid) {
          setAccessResult({
            hasAccess: false,
            reason: 'session_invalid',
            missingPermissions: [],
            missingRoles: []
          });
        } else {
          // Session is valid, proceed to permission checks
          setAccessResult(prev => ({
            ...prev,
            hasAccess: true,
            reason: 'session_valid'
          }));
        }
      } catch (error) {
        console.error('Error validating authentication:', error);
        setAccessResult({
          hasAccess: false,
          reason: 'validation_error',
          missingPermissions: [],
          missingRoles: []
        });
      } finally {
        setAuthValidating(false);
      }
    };

    validateAuth();
  }, [loading, isAuthenticated, config.requireAuth, validateAndRefreshSession]);

  // Permission and role validation
  useEffect(() => {
    const validateAccess = async () => {
      if (!isAuthenticated || !config.requireAuth || accessResult.hasAccess !== true) {
        return;
      }
      
      setPermissionValidating(true);
      try {
        let hasAccess = true;
        let reason = 'access_granted';
        const missingPermissions = [];
        const missingRoles = [];

        // Check profile completion requirement
        if (config.requireCompleteProfile && user && !isProfileComplete(user)) {
          // Allow access to profile completion routes
          if (location.pathname === '/login' && location.search.includes('step=profile')) {
            // Profile completion route is allowed
          } else {
            hasAccess = false;
            reason = 'profile_incomplete';
          }
        }

        // Check pilot user requirement
        if (hasAccess && config.requirePilot && !isPilotUser) {
          hasAccess = false;
          reason = 'pilot_required';
        }

        // Check permissions if specified
        if (hasAccess && config.permissions.length > 0) {
          if (config.allowPartialAccess) {
            // Check each permission individually
            for (const permission of config.permissions) {
              const hasPermission = await isAccessGranted([permission]);
              if (!hasPermission) {
                missingPermissions.push(permission);
              }
            }
            // Allow access if at least one permission is granted
            if (missingPermissions.length === config.permissions.length) {
              hasAccess = false;
              reason = 'insufficient_permissions';
            }
          } else {
            // Require all permissions
            const hasAllPermissions = await isAccessGranted(config.permissions);
            if (!hasAllPermissions) {
              hasAccess = false;
              reason = 'insufficient_permissions';
              // Identify missing permissions
              for (const permission of config.permissions) {
                const hasPermission = await isAccessGranted([permission]);
                if (!hasPermission) {
                  missingPermissions.push(permission);
                }
              }
            }
          }
        }

        // Check roles if specified
        if (hasAccess && config.roles.length > 0) {
          const roleChecks = await Promise.all(
            config.roles.map(async (role) => {
              const hasRoleResult = await hasRole(role);
              if (!hasRoleResult) {
                missingRoles.push(role);
              }
              return hasRoleResult;
            })
          );
          
          const hasRequiredRole = roleChecks.some(hasRoleResult => hasRoleResult);
          if (!hasRequiredRole) {
            hasAccess = false;
            reason = 'insufficient_roles';
          }
        }

        // Custom validation if provided
        if (hasAccess && config.customValidator) {
          try {
            const customResult = await config.customValidator({
              user,
              location,
              isAuthenticated,
              permissions: config.permissions,
              roles: config.roles
            });
            
            if (typeof customResult === 'boolean') {
              hasAccess = customResult;
              if (!hasAccess) {
                reason = 'custom_validation_failed';
              }
            } else if (typeof customResult === 'object') {
              hasAccess = customResult.hasAccess;
              reason = customResult.reason || reason;
            }
          } catch (error) {
            console.error('Custom validator error:', error);
            hasAccess = false;
            reason = 'custom_validation_error';
          }
        }

        // Route-specific access check
        if (hasAccess) {
          const routeName = location.pathname.substring(1) || 'overview';
          const canAccess = await canAccessRoute(routeName);
          if (!canAccess) {
            hasAccess = false;
            reason = 'route_access_denied';
          }
        }

        setAccessResult({
          hasAccess,
          reason,
          missingPermissions,
          missingRoles
        });

        // Call callbacks
        if (hasAccess && onAccessGranted) {
          onAccessGranted({ user, location, reason });
        } else if (!hasAccess && onAccessDenied) {
          onAccessDenied({ 
            user, 
            location, 
            reason, 
            missingPermissions, 
            missingRoles 
          });
        }

      } catch (error) {
        console.error('Error validating access:', error);
        setAccessResult({
          hasAccess: false,
          reason: 'validation_error',
          missingPermissions: [],
          missingRoles: []
        });
        
        if (onAccessDenied) {
          onAccessDenied({ user, location, reason: 'validation_error', error });
        }
      } finally {
        setPermissionValidating(false);
      }
    };

    if (accessResult.hasAccess === true && isAuthenticated) {
      validateAccess();
    }
  }, [
    isAuthenticated,
    user,
    location,
    accessResult.hasAccess,
    config,
    isProfileComplete,
    isAccessGranted,
    hasRole,
    canAccessRoute,
    onAccessGranted,
    onAccessDenied,
    isPilotUser
  ]);

  // Loading states for authentication checks
  if (loading || authValidating || permissionValidating || accessResult.hasAccess === null) {
    if (loadingComponent) {
      return loadingComponent;
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner size="xl" />
          <p className="mt-4 text-gray-600">
            {loading && "Initializing..."}
            {authValidating && "Validating session..."}
            {permissionValidating && "Checking permissions..."}
            {accessResult.hasAccess === null && !loading && !authValidating && !permissionValidating && "Loading..."}
          </p>
        </div>
      </div>
    );
  }

  // Handle both protected and public route scenarios
  if (!config.requireAuth) {
    // Public route handling
    if (isAuthenticated && location.pathname === '/login') {
      // Redirect authenticated users away from login
      if (user && isProfileComplete(user)) {
        return <Navigate to="/overview" replace />;
      } else {
        return <Navigate to="/login?step=profile" replace />;
      }
    }
    return children;
  }

  // Protected route handling
  if (!accessResult.hasAccess) {
    // Custom fallback component
    if (fallback) {
      return fallback;
    }

    // Handle different access denial reasons
    switch (accessResult.reason) {
      case 'session_invalid':
      case 'validation_error': {
        // Redirect to login with return location
        const state = location.pathname !== '/login' ? { from: location } : undefined;
        return <Navigate to={config.redirectTo} state={state} replace />;
      }
        
      case 'profile_incomplete': {
        // Redirect to profile completion
        const profileState = location.pathname !== '/login' ? { from: location } : undefined;
        return <Navigate to="/login?step=profile" state={profileState} replace />;
      }
        
      case 'insufficient_permissions':
      case 'insufficient_roles':
      case 'route_access_denied':
      case 'custom_validation_failed':
      case 'pilot_required':
        // Access denied - redirect to unauthorized page or login
        return <Navigate to={config.redirectTo} replace />;
        
      default:
        // Default redirect
        return <Navigate to={config.redirectTo} replace />;
    }
  }

  // Access granted - render children
  return children;
};

export default AuthWrapper;