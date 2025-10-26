import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar.jsx';

const MainLayout = () => {
    return (
        <div className="bg-gray-50 h-screen flex text-gray-900">
            <Sidebar />
            
            <div className="flex-1 overflow-y-auto">
                <Outlet />
            </div>
        </div>
    );
};

export default MainLayout;
