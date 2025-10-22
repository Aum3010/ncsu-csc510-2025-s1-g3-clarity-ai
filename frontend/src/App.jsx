import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import RequirementsDashboard from './views/RequirementsDashboard';
import StudioModal from './components/StudioModal';
import './App.css'; 
import './index.css'; 

const PlaceholderView = ({ viewName }) => (
    <div className="p-8 w-full">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">{viewName} View</h2>
        <p className="text-gray-400">This is a placeholder for the {viewName} feature.</p>
    </div>
);

function App() {
    const [isStudioOpen, setIsStudioOpen] = useState(false); 
    const [refreshSignal, setRefreshSignal] = useState(0);

    const refreshDashboard = () => {
        setRefreshSignal(prev => prev + 1);
    };

    return (
        <>
            <Routes>
                <Route element={<MainLayout onStudioOpen={() => setIsStudioOpen(true)} />}>
                    
                    {/* Pass refreshSignal to the Dashboard components */}
                    <Route index element={<RequirementsDashboard refreshSignal={refreshSignal} />} /> 
                    <Route path="requirements" element={<RequirementsDashboard refreshSignal={refreshSignal} />} />
                    
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
                onAnalysisSuccess={refreshDashboard}
            />
        </>
    );
}

export default App;