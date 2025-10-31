import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../lib/auth-context.jsx';
import LogoutButton from './LogoutButton.jsx';



const views = [
    { name: 'Overview', icon: '📊', path: '/overview', permissions: ['overview'] },
    { name: 'Requirements', icon: '📝', path: '/requirements', permissions: ['requirements'] },
    { name: 'Documents', icon: '📂', path: '/documents', permissions: ['documents'] },
    { name: 'Integrations', icon: '🔌', path: '/integrations', permissions: ['integrations'], pilotOnly: true },
    { name: 'Beta Features', icon: '🧪', path: '/beta', permissions: ['beta_features'], pilotOnly: true },
    { name: 'Team', icon: '👥', path: '/team', permissions: ['team'], adminOnly: true },
];

const Sidebar = () => {
    const { user, isAccessGranted, isPilotUser, hasRole } = useAuth();
    const [visibleViews, setVisibleViews] = React.useState([]);

    // Filter views based on user permissions and roles
    React.useEffect(() => {
        const filterViews = async () => {
            if (!user) {
                setVisibleViews([]);
                return;
            }

            const filteredViews = [];
            
            for (const view of views) {
                let shouldShow = true;

                // Check if view requires pilot user access
                if (view.pilotOnly && !isPilotUser) {
                    shouldShow = false;
                }

                // Check if view requires admin role
                if (view.adminOnly) {
                    const isAdmin = await hasRole('admin');
                    if (!isAdmin) {
                        shouldShow = false;
                    }
                }

                // Check specific permissions
                if (view.permissions && view.permissions.length > 0) {
                    const hasAccess = await isAccessGranted(view.permissions);
                    if (!hasAccess) {
                        shouldShow = false;
                    }
                }

                if (shouldShow) {
                    filteredViews.push(view);
                }
            }

            setVisibleViews(filteredViews);
        };

        filterViews();
    }, [user, isPilotUser, isAccessGranted, hasRole]);

    return (
        <div className="bg-white text-gray-900 w-64 flex flex-col p-4 space-y-4 h-full shadow-lg shrink-0">
            <h1 className="text-2xl font-bold border-b border-gray-200 pb-4 text-purple-700">Clarity</h1>
            
            <nav className="flex flex-col space-y-1 pt-4 flex-1">
                {visibleViews.map((view) => (
                    <NavLink
                        key={view.name}
                        to={view.path}
                        end={view.path === '/overview'} 
                        className={({ isActive }) => 
                            `flex items-center space-x-3 p-2 rounded-lg cursor-pointer transition-colors duration-150
                            ${isActive 
                                ? 'bg-purple-100 text-purple-700 font-semibold' // Active link
                                : 'hover:bg-gray-100 text-gray-700'}` // Hover/default
                        }
                    >
                        <span>{view.icon}</span>
                        <span>{view.name}</span>
                        {view.pilotOnly && (
                            <span className="ml-auto text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full">
                                Beta
                            </span>
                        )}
                        {view.adminOnly && (
                            <span className="ml-auto text-xs bg-red-100 text-red-600 px-2 py-1 rounded-full">
                                Admin
                            </span>
                        )}
                    </NavLink>
                ))}
            </nav>

            {/* User info and logout section */}
            <div className="border-t border-gray-200 pt-4 space-y-3">
                {user && (
                    <div className="px-2 py-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                            {user.metadata?.first_name && user.metadata?.last_name 
                                ? `${user.metadata.first_name} ${user.metadata.last_name}`
                                : user.email
                            }
                        </p>
                        <p className="text-xs text-gray-500 truncate">{user.email}</p>
                        {isPilotUser && (
                            <p className="text-xs text-blue-600 font-medium">Pilot User</p>
                        )}
                    </div>
                )}
                <LogoutButton />
            </div>
        </div>
    );
};

export default Sidebar;
