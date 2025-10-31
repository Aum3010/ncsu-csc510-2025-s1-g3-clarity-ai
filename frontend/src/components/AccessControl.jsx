import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../lib/auth-context.jsx';

/**
 * AccessControl component for conditional rendering based on user permissions
 * 
 * @param {Object} props
 * @param {string[]} props.permissions - Array of required permissions
 * @param {string[]} props.roles - Array of required roles
 * @param {boolean} props.requirePilot - Whether pilot user status is required
 * @param {boolean} props.requireAdmin - Whether admin role is required
 * @param {React.ReactNode} props.children - Content to render if access is granted
 * @param {React.ReactNode} props.fallback - Content to render if access is denied
 * @param {boolean} props.showLoading - Whether to show loading state during permission check
 */
const AccessControl = ({ 
    permissions = [], 
    roles = [], 
    requirePilot = false, 
    requireAdmin = false,
    children, 
    fallback = null,
    showLoading = true 
}) => {
    const { isAccessGranted, hasRole, isPilotUser, isAuthenticated, loading } = useAuth();
    const [hasAccess, setHasAccess] = useState(false);
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        const checkAccess = async () => {
            if (!isAuthenticated || loading) {
                setHasAccess(false);
                setIsChecking(false);
                return;
            }

            try {
                setIsChecking(true);

                // Check pilot user requirement
                if (requirePilot && !isPilotUser) {
                    setHasAccess(false);
                    return;
                }

                // Check admin requirement
                if (requireAdmin) {
                    const isAdmin = await hasRole('admin');
                    if (!isAdmin) {
                        setHasAccess(false);
                        return;
                    }
                }

                // Check specific roles
                if (roles.length > 0) {
                    for (const role of roles) {
                        const hasRequiredRole = await hasRole(role);
                        if (!hasRequiredRole) {
                            setHasAccess(false);
                            return;
                        }
                    }
                }

                // Check permissions
                if (permissions.length > 0) {
                    const hasPermissions = await isAccessGranted(permissions);
                    if (!hasPermissions) {
                        setHasAccess(false);
                        return;
                    }
                }

                // If all checks pass, grant access
                setHasAccess(true);
            } catch (error) {
                console.error('Error checking access:', error);
                setHasAccess(false);
            } finally {
                setIsChecking(false);
            }
        };

        checkAccess();
    }, [
        isAuthenticated, 
        loading, 
        permissions, 
        roles, 
        requirePilot, 
        requireAdmin, 
        isPilotUser, 
        isAccessGranted, 
        hasRole
    ]);

    // Show loading state if still checking and loading is enabled
    if (isChecking && showLoading) {
        return (
            <div className="flex items-center justify-center p-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600"></div>
                <span className="ml-2 text-sm text-gray-600">Checking permissions...</span>
            </div>
        );
    }

    // Render children if access is granted, otherwise render fallback
    return hasAccess ? children : fallback;
};

// Export the hook separately to avoid fast refresh issues
const useAccessControl = ({ 
    permissions = [], 
    roles = [], 
    requirePilot = false, 
    requireAdmin = false 
} = {}) => {
    const { isAccessGranted, hasRole, isPilotUser, isAuthenticated, loading } = useAuth();
    const [hasAccess, setHasAccess] = useState(false);
    const [isChecking, setIsChecking] = useState(true);

    const checkAccess = useCallback(async () => {
        if (!isAuthenticated || loading) {
            setHasAccess(false);
            setIsChecking(false);
            return false;
        }

        try {
            setIsChecking(true);

            // Check pilot user requirement
            if (requirePilot && !isPilotUser) {
                setHasAccess(false);
                return false;
            }

            // Check admin requirement
            if (requireAdmin) {
                const isAdmin = await hasRole('admin');
                if (!isAdmin) {
                    setHasAccess(false);
                    return false;
                }
            }

            // Check specific roles
            if (roles.length > 0) {
                for (const role of roles) {
                    const hasRequiredRole = await hasRole(role);
                    if (!hasRequiredRole) {
                        setHasAccess(false);
                        return false;
                    }
                }
            }

            // Check permissions
            if (permissions.length > 0) {
                const hasPermissions = await isAccessGranted(permissions);
                if (!hasPermissions) {
                    setHasAccess(false);
                    return false;
                }
            }

            // If all checks pass, grant access
            setHasAccess(true);
            return true;
        } catch (error) {
            console.error('Error checking access:', error);
            setHasAccess(false);
            return false;
        } finally {
            setIsChecking(false);
        }
    }, [
        isAuthenticated, 
        loading, 
        permissions, 
        roles, 
        requirePilot, 
        requireAdmin, 
        isPilotUser, 
        isAccessGranted, 
        hasRole
    ]);

    useEffect(() => {
        checkAccess();
    }, [checkAccess]);

    return { hasAccess, isChecking, checkAccess };
};

// eslint-disable-next-line react-refresh/only-export-components
export { useAccessControl };
export default AccessControl;