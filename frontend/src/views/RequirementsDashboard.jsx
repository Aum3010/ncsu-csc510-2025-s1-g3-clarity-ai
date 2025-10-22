import React, { useState, useEffect } from 'react';
import axios from 'axios';
import RequirementCard from '../components/RequirementCard';

const RequirementsDashboard = () => {
  const [requirements, setRequirements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRequirements = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:5000/api/requirements');
        setRequirements(response.data);
      } catch (err) {
        console.error("Error fetching requirements:", err);
        setError("Failed to load requirements. Is the backend server running?");
      } finally {
        setIsLoading(false);
      }
    };

    fetchRequirements();
  }, []);

  if (isLoading) {
    return <div className="flex-1 p-8 text-center text-lg text-purple-600">Loading Dashboard Data...</div>;
  }

  if (error) {
    return <div className="flex-1 p-8 text-center text-lg text-red-600">Error: {error}</div>;
  }

  return (
    // Background is the main app background, text is dark
    <div className="flex-1 p-8 text-gray-900">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-900">Project Requirements Dashboard</h2>
        {/* Filtering controls matching the mockup */}
        <div className="flex space-x-3 text-sm">
          <select className="bg-white border border-gray-300 p-2 rounded-lg">
            <option>All Status</option>
          </select>
          <select className="bg-white border border-gray-300 p-2 rounded-lg">
            <option>All Priority</option>
          </select>
        </div>
      </div>

      <p className="text-gray-600 mb-8">
        Manage and track all project requirements in one place. Found {requirements.length} requirements.
      </p>

      {/* List of Requirement Cards */}
      <div className="space-y-6">
        {requirements.map((req) => (
          <RequirementCard key={req.id} requirement={req} />
        ))}
      </div>
    </div>
  );
};

export default RequirementsDashboard;