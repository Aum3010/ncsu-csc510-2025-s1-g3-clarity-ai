import React, { useState, useEffect } from 'react';
import axios from 'axios';
import RequirementCard from '../components/RequirementCard.jsx'; 

const RequirementsDashboard = ({ refreshSignal, onTriggerRefresh }) => {
  const [requirements, setRequirements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);

  // Function to fetch data (unchanged)
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

  // Fetch data initially and whenever the refreshSignal changes
  useEffect(() => {
    fetchRequirements();
  }, [refreshSignal]); // This dependency is key!

  // New function to handle regeneration
  const handleRegenerate = async () => {
    if (!window.confirm('This will re-analyze all documents and generate new requirements. This may take a moment. Continue?')) {
        return;
    }
    
    try {
        setIsGenerating(true);
        setError(null);
        await axios.post('http://127.0.0.1:5000/api/requirements/generate');

        onTriggerRefresh();
        
    } catch (err) {
        console.error("Error generating requirements:", err);
        setError("Failed to generate new requirements.");
    } finally {
        setIsGenerating(false);
    }
  };


  if (isLoading && requirements.length === 0) {
    return <div className="flex-1 p-8 text-center text-lg text-purple-600">Loading Dashboard Data...</div>;
  }

  return (
    <div className="flex-1 p-8 text-gray-900">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-900">Project Requirements</h2>
        <div className="flex space-x-3">
          {/* Manual refresh button for robustness */}
          <button 
            onClick={fetchRequirements} 
            disabled={isLoading || isGenerating}
            className="bg-gray-200 hover:bg-gray-300 text-gray-800 p-2 rounded-lg disabled:opacity-50"
            title="Refresh List"
          >
            🔄
          </button>
          {/* New Regenerate Button */}
          <button 
            onClick={handleRegenerate} 
            disabled={isGenerating || isLoading}
            className="bg-orange-500 hover:bg-orange-600 text-white font-semibold py-2 px-4 rounded-lg disabled:opacity-50"
          >
            {isGenerating ? 'Generating...' : 'Regenerate All'}
          </button>
        </div>
      </div>

      <p className="text-gray-600 mb-8">
        Found {requirements.length} requirements. These are generated from the files in the Documents tab.
      </p>

      {error && <div className="p-4 mb-4 text-center text-lg text-red-600 bg-red-100 rounded-lg">Error: {error}</div>}

      <div className="space-y-6">
        {requirements.map((req) => (
          <RequirementCard key={req.id} requirement={req} />
        ))}
        {requirements.length === 0 && !isLoading && (
            <p className="text-gray-500 text-center py-10">No requirements found. Upload documents to get started!</p>
        )}
      </div>
    </div>
  );
};

export default RequirementsDashboard;
