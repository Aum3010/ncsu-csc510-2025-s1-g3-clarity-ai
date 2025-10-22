import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import RequirementsDashboard from './views/RequirementsDashboard';
import StudioModal from './components/StudioModal';
import './App.css'; 
import './index.css'; 

// Placeholder Components for future views
const PlaceholderView = ({ viewName }) => (
    // Updated text and background colors
    <div className="p-8 w-full">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">{viewName} View</h2>
        <p className="text-gray-600">This is a placeholder for the {viewName} feature.</p>
    </div>
);

function App() {
    const [isStudioOpen, setIsStudioOpen] = useState(false); 

    return (
        <>
            <Routes>
                <Route element={<MainLayout onStudioOpen={() => setIsStudioOpen(true)} />}>
                    
                    <Route index element={<RequirementsDashboard />} /> 
                    <Route path="requirements" element={<RequirementsDashboard />} />
                    
                    <Route path="overview" element={<PlaceholderView viewName="Overview" />} />
                    <Route path="documents" element={<PlaceholderView viewName="Documents" />} />
                    <Route path="integrations" element={<PlaceholderView viewName="Integrations" />} />
                    <Route path="team" element={<PlaceholderView viewName="Team" />} />
                    
                    <Route path="*" element={<PlaceholderView viewName="404 Not Found" />} />
                </Route>
            </Routes>

            <StudioModal 
                isOpen={isStudioOpen} 
                onClose={() => setIsStudioOpen(false)}
            />
        </>
    );
}

export default App;