import React, { useState, useEffect } from 'react';
import axios from 'axios';
import RequirementCard from '../components/RequirementCard';

// The component now accepts a 'refreshSignal' prop
const RequirementsDashboard = ({ refreshSignal }) => {
  const [requirements, setRequirements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Function to fetch data
  const fetchRequirements = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('http://127.0.0.1:5000/api/requirements');
      setRequirements(response.data);
      setError(null);
    } catch (err) {
      console.error("Error fetching requirements:", err);
      setError("Failed to load requirements. Is the backend server running?");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Fetch data initially and whenever the refreshSignal changes
    fetchRequirements();
  }, [refreshSignal]); // Dependency array includes refreshSignal

  if (isLoading) {
    return <div className="flex-1 p-8 text-center text-lg text-purple-600">Loading Dashboard Data...</div>;
  }

  if (error) {
    return <div className="flex-1 p-8 text-center text-lg text-red-600">Error: {error}</div>;
  }

  return (
    <div className="flex-1 p-8 text-gray-900">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-900">Project Requirements Dashboard</h2>
        <div className="flex space-x-3 text-sm">
          <select className="bg-white border border-gray-300 p-2 rounded-lg">
            <option>All Status</option>
          </select>
          <select className="bg-white border border-gray-300 p-2 rounded-lg">
            <option>All Priority</option>
          </select>
          {/* Manual refresh button for robustness */}
          <button onClick={() => fetchRequirements()} className="bg-gray-200 hover:bg-gray-300 text-gray-800 p-2 rounded-lg">
            🔄
          </button>
        </div>
      </div>

      <p className="text-gray-600 mb-8">
        Manage and track all project requirements in one place. Found {requirements.length} requirements.
      </p>

      <div className="space-y-6">
        {requirements.map((req) => (
          <RequirementCard key={req.id} requirement={req} />
        ))}
        {requirements.length === 0 && <p className="text-gray-500 text-center py-10">No requirements found. Upload a file and run analysis!</p>}
      </div>
    </div>
  );
};

export default RequirementsDashboard;