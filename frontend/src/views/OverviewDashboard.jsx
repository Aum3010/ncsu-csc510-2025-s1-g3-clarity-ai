import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import apiService from '../lib/api-service.js';
import AccessControl from '../components/AccessControl.jsx';



const OverviewDashboard = ({ refreshSignal }) => {
  const [summary, setSummary] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    
    const fetchSummary = async () => {
      if (!isMounted) return;
      
      try {
        setIsLoading(true);
        const response = await apiService.coreApi('/api/summary');
        if (!isMounted) return;
        setSummary(response.summary);
        setError(null);
      } catch (err) {
        if (!isMounted) return;
        console.error("Error fetching summary:", err);
        if (err.message.includes('Authentication failed') || err.message.includes('Session expired')) {
          setError("Authentication required. Please log in again.");
        } else {
          setError("Failed to load project summary. Have any documents been processed?");
        }
        setSummary('');
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchSummary();
    
    return () => {
      isMounted = false;
    };
  }, [refreshSignal]); // Refreshes whenever documents are updated!

  return (
    <div className="flex-1 p-8 text-gray-900">
      <h2 className="text-3xl font-bold text-gray-900 mb-8">Project Overview</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Navigation Cards */}
        <DashboardCard
          title="Manage Documents"
          description="Upload, view, and manage all source documents for the project."
          linkTo="/documents"
          icon="📂"
        />
        <DashboardCard
          title="View Requirements"
          description="See all generated requirements, user stories, and tasks."
          linkTo="/requirements"
          icon="📝"
        />
         <DashboardCard
          title="Manage Team"
          description="Add or remove team members from the project."
          linkTo="/team"
          icon="👥"
        />
        
        {/* Pilot-only features */}
        <AccessControl 
          requirePilot={true} 
          permissions={['beta_features']}
          fallback={null}
        >
          <DashboardCard
            title="Beta Features"
            description="Access experimental features and advanced analytics."
            linkTo="/beta"
            icon="🧪"
          />
        </AccessControl>
        
        <AccessControl 
          permissions={['integrations']}
          fallback={null}
        >
          <DashboardCard
            title="Integrations"
            description="Connect with external tools and services."
            linkTo="/integrations"
            icon="🔌"
          />
        </AccessControl>
      </div>

      {/* Automated Summary Card */}
      <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-purple-400">
        <h3 className="text-xl font-semibold text-gray-900 mb-3">Automated Project Summary</h3>
        {isLoading && <p className="text-gray-600">Generating summary...</p>}
        {error && <p className="text-red-600">{error}</p>}
        {summary && !isLoading && (
          <pre className="text-gray-700 whitespace-pre-wrap font-sans">{summary}</pre>
        )}
        {!summary && !isLoading && !error && (
            <p className="text-gray-500">No summary available. Upload documents to generate one.</p>
        )}
      </div>
    </div>
  );
};

const DashboardCard = ({ title, description, linkTo, icon }) => (
  <Link to={linkTo} className="block bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
    <div className="flex items-center space-x-4 mb-2">
      <span className="text-3xl">{icon}</span>
      <h4 className="text-xl font-semibold text-gray-900">{title}</h4>
    </div>
    <p className="text-gray-600">{description}</p>
  </Link>
);


export default OverviewDashboard;
