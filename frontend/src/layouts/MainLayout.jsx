import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';

const MainLayout = ({ onStudioOpen }) => {
    return (
        <div className="bg-gray-50 min-h-screen flex text-gray-900 h-full"> 
            <Sidebar onStudioOpen={onStudioOpen} />
            
            <div className="flex-1 overflow-y-auto">
                <Outlet />
            </div>
        </div>
    );
};

export default MainLayout;