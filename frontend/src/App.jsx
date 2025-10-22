import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout.jsx';
import OverviewDashboard from './views/OverviewDashboard.jsx';
import RequirementsDashboard from './views/RequirementsDashboard.jsx';
import DocumentsDashboard from './views/DocumentsDashboard.jsx';
import './App.css'; 
import './index.css'; 

// A simple placeholder for views you haven't built yet
const PlaceholderView = ({ viewName }) => (
    <div className="p-8 w-full">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">{viewName} View</h2>
        <p className="text-gray-400">This is a placeholder for the {viewName} feature.</p>
    </div>
);

function App() {

    const [refreshSignal, setRefreshSignal] = useState(0);
    const triggerRefresh = () => {
        setRefreshSignal(prev => prev + 1);
    };

    return (
        <Routes>
            <Route element={<MainLayout />}>
                
                {/* Default route redirects to overview */}
                <Route index element={<Navigate to="/overview" replace />} />
                
                {/* Pass refreshSignal to all dashboards that need to auto-update */}
                <Route 
                    path="overview" 
                    element={<OverviewDashboard refreshSignal={refreshSignal} />} 
                />
                <Route 
                    path="requirements" 
                    element={<RequirementsDashboard refreshSignal={refreshSignal} onTriggerRefresh={triggerRefresh} />} 
                />
                <Route 
                    path="documents" 
                    element={<DocumentsDashboard onTriggerRefresh={triggerRefresh} />} 
                />
                
                {/* Other routes remain placeholders for now */}
                <Route path="integrations" element={<PlaceholderView viewName="Integrations" />} />
                <Route path="team" element={<PlaceholderView viewName="Team" />} />
                
                <Route path="*" element={<PlaceholderView viewName="404 Not Found" />} />
            </Route>
        </Routes>
    );
}

export default App;
