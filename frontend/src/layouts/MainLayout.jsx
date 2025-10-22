import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/sidebar.jsx';

const MainLayout = ({ onStudioOpen }) => {
    return (
        <div className="bg-gray-50 h-screen flex text-gray-900">
            <Sidebar onStudioOpen={onStudioOpen} />
            
            <div className="flex-1 overflow-y-auto">
                <Outlet />
            </div>
        </div>
    );
};

export default MainLayout;