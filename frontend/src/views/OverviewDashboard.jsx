import React from 'react'; 
import { Link } from 'react-router-dom';
import AccessControl from '../components/AccessControl.jsx';
import AutomatedSummary from '../components/Summary.jsx'; 

const OverviewDashboard = ({ refreshSignal }) => {

  return (
    <div className="flex-1 p-8 text-gray-900">
      <h2 className="text-3xl font-bold text-gray-900 mb-8">Project Overview</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
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
         {/* <DashboardCard
          title="Manage Team"
          description="Add or remove team members from the project."
          linkTo="/team"
          icon="👥"
        />
         */}
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

      <AutomatedSummary refreshSignal={refreshSignal} />

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
