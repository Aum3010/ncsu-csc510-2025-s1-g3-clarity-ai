import React from 'react';
import { NavLink } from 'react-router-dom';


const views = [
    { name: 'Overview', icon: '📊', path: '/overview' },
    { name: 'Requirements', icon: '📝', path: '/requirements' },
    { name: 'Documents', icon: '📂', path: '/documents' },
    { name: 'Integrations', icon: '🔌', path: '/integrations' },
    { name: 'Team', icon: '👥', path: '/team' },
];

const Sidebar = () => {
    return (
        <div className="bg-white text-gray-900 w-64 flex flex-col p-4 space-y-4 h-full shadow-lg shrink-0">
            <h1 className="text-2xl font-bold border-b border-gray-200 pb-4 text-purple-700">Clarity</h1>
            
            <nav className="flex flex-col space-y-1 pt-4">
                {views.map((view) => (
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
                    </NavLink>
                ))}
            </nav>

        </div>
    );
};

export default Sidebar;
