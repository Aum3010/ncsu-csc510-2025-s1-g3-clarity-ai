import React, { useState } from 'react';
import { useAuth } from '../lib/auth-context.jsx';

const LogoutButton = ({ className = '', showText = true }) => {
    const { signOut } = useAuth();
    const [isLoggingOut, setIsLoggingOut] = useState(false);

    const handleLogout = async () => {
        try {
            setIsLoggingOut(true);
            await signOut();
        } catch (error) {
            console.error('Logout error:', error);
            // Even if logout fails, we still want to clear local state
            // The signOut function should handle this gracefully
        } finally {
            setIsLoggingOut(false);
        }
    };

    return (
        <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            className={`flex items-center space-x-3 p-2 rounded-lg cursor-pointer transition-colors duration-150 
                hover:bg-red-50 text-red-600 hover:text-red-700 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
            title="Sign out"
        >
            <span className="text-lg">
                {isLoggingOut ? '⏳' : '🚪'}
            </span>
            {showText && (
                <span className="font-medium">
                    {isLoggingOut ? 'Signing out...' : 'Sign out'}
                </span>
            )}
        </button>
    );
};

export default LogoutButton;