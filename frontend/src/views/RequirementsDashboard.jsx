import React, { useState, useEffect } from 'react';
import RequirementCard from '../components/RequirementCard.jsx';
import apiService from '../lib/api-service.js'; 

const RequirementsDashboard = ({ refreshSignal, onTriggerRefresh }) => {
  const [requirements, setRequirements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [enableRealTimeAnalysis, setEnableRealTimeAnalysis] = useState(false);
  const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 });
  const [batchResults, setBatchResults] = useState(null);
  const [showBatchResults, setShowBatchResults] = useState(false);
  const batchCancelRef = React.useRef(false);

  // Function to fetch data (unchanged)
  const fetchRequirements = async () => {
    try {
      setIsLoading(true);
      const response = await apiService.coreApi('/api/requirements');
      setRequirements(response);
      setError(null);
    } catch (err) {
      console.error("Error fetching requirements:", err);
      if (err.message.includes('Authentication failed') || err.message.includes('Session expired')) {
        setError("Authentication required. Please log in again.");
      } else {
        setError("Failed to load requirements. Is the backend server running?");
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch data initially and whenever the refreshSignal changes
  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      if (!isMounted) return;
      await fetchRequirements();
    };
    
    loadData();
    
    return () => {
      isMounted = false;
    };
  }, [refreshSignal]); // This dependency is key!

  // New function to handle regeneration
  const handleRegenerate = async () => {
    if (!window.confirm('This will re-analyze all documents and generate new requirements. This may take a moment. Continue?')) {
        return;
    }
    
    try {
        setIsGenerating(true);
        setError(null);
        await apiService.coreApi('/api/requirements/generate', { method: 'POST' });

        onTriggerRefresh();
        
    } catch (err) {
        console.error("Error generating requirements:", err);
        setError("Failed to generate new requirements.");
    } finally {
        setIsGenerating(false);
    }
  };

  // Batch analysis handler
  const handleBatchAnalyze = async () => {
    if (requirements.length === 0) {
      setError("No requirements to analyze");
      return;
    }

    if (!window.confirm(`This will analyze all ${requirements.length} requirements for ambiguity. Continue?`)) {
      return;
    }

    setIsBatchAnalyzing(true);
    setBatchProgress({ current: 0, total: requirements.length });
    setBatchResults(null);
    setShowBatchResults(false);
    setError(null);
    batchCancelRef.current = false;

    try {
      const requirementIds = requirements.map(req => req.id);
      const results = [];
      let totalTerms = 0;
      let totalResolved = 0;

      // Process in batches to avoid overwhelming the backend
      const batchSize = 5;
      for (let i = 0; i < requirementIds.length; i += batchSize) {
        // Check for cancellation
        if (batchCancelRef.current) {
          setError("Batch analysis cancelled");
          break;
        }

        const batch = requirementIds.slice(i, i + batchSize);
        
        try {
          const batchResults = await apiService.batchAnalyzeRequirements(batch);
          results.push(...batchResults);

          // Update progress
          setBatchProgress({ current: Math.min(i + batchSize, requirementIds.length), total: requirementIds.length });

          // Accumulate statistics
          batchResults.forEach(result => {
            totalTerms += result.total_terms_flagged || 0;
            totalResolved += result.terms_resolved || 0;
          });
        } catch (err) {
          console.error(`Error analyzing batch ${i / batchSize + 1}:`, err);
          // Continue with next batch even if one fails
        }
      }

      if (!batchCancelRef.current) {
        // Set final results
        setBatchResults({
          totalRequirements: requirements.length,
          analyzedRequirements: results.length,
          totalTerms,
          totalResolved,
          results
        });
        setShowBatchResults(true);
      }
    } catch (err) {
      console.error("Batch analysis error:", err);
      setError(err.message || "Failed to complete batch analysis");
    } finally {
      setIsBatchAnalyzing(false);
      setBatchProgress({ current: 0, total: 0 });
    }
  };

  // Cancel batch analysis
  const handleCancelBatchAnalysis = () => {
    batchCancelRef.current = true;
  };


  if (isLoading && requirements.length === 0) {
    return <div className="flex-1 p-8 text-center text-lg text-purple-600">Loading Dashboard Data...</div>;
  }

  return (
    <div className="flex-1 p-8 text-gray-900">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-900">Project Requirements</h2>
        <div className="flex space-x-3">
          {/* Real-time analysis toggle */}
          <button
            onClick={() => setEnableRealTimeAnalysis(!enableRealTimeAnalysis)}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              enableRealTimeAnalysis
                ? 'bg-orange-500 text-white hover:bg-orange-600'
                : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
            }`}
            title="Toggle real-time ambiguity analysis"
          >
            {enableRealTimeAnalysis ? '⚡ Real-time ON' : '⚡ Real-time OFF'}
          </button>
          {/* Batch analyze button */}
          <button
            onClick={handleBatchAnalyze}
            disabled={isBatchAnalyzing || isLoading || isGenerating || requirements.length === 0}
            className="bg-purple-500 hover:bg-purple-600 text-white font-semibold py-2 px-4 rounded-lg disabled:opacity-50 transition-colors"
            title="Analyze all requirements for ambiguity"
          >
            {isBatchAnalyzing ? 'Analyzing...' : '🔍 Analyze All Requirements'}
          </button>
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

      {/* Batch analysis progress indicator */}
      {isBatchAnalyzing && (
        <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600"></div>
              <span className="text-purple-900 font-semibold">
                Analyzing requirements... {batchProgress.current} / {batchProgress.total}
              </span>
            </div>
            <button
              onClick={handleCancelBatchAnalysis}
              className="px-3 py-1 bg-red-500 hover:bg-red-600 text-white text-sm rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
          <div className="w-full bg-purple-200 rounded-full h-3">
            <div
              className="bg-purple-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${(batchProgress.current / batchProgress.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Batch analysis results summary */}
      {showBatchResults && batchResults && (
        <div className="mb-6 p-6 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-green-900">Batch Analysis Complete</h3>
            <button
              onClick={() => setShowBatchResults(false)}
              className="text-green-700 hover:text-green-900 text-2xl"
            >
              ×
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Requirements Analyzed</p>
              <p className="text-2xl font-bold text-gray-900">
                {batchResults.analyzedRequirements} / {batchResults.totalRequirements}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Total Ambiguous Terms</p>
              <p className="text-2xl font-bold text-orange-600">{batchResults.totalTerms}</p>
            </div>
            <div className="bg-white p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Terms Resolved</p>
              <p className="text-2xl font-bold text-green-600">{batchResults.totalResolved}</p>
            </div>
            <div className="bg-white p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Pending Clarifications</p>
              <p className="text-2xl font-bold text-purple-600">
                {batchResults.totalTerms - batchResults.totalResolved}
              </p>
            </div>
          </div>
          {batchResults.totalTerms > 0 && (
            <div className="mt-4">
              <p className="text-sm text-gray-600 mb-2">Overall Progress</p>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-green-600 h-3 rounded-full transition-all duration-300"
                  style={{ 
                    width: `${(batchResults.totalResolved / batchResults.totalTerms) * 100}%` 
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {Math.round((batchResults.totalResolved / batchResults.totalTerms) * 100)}% of ambiguous terms resolved
              </p>
            </div>
          )}
        </div>
      )}

      <div className="space-y-6">
        {requirements.map((req) => (
          <RequirementCard 
            key={req.id} 
            requirement={req} 
            enableRealTimeAnalysis={enableRealTimeAnalysis}
          />
        ))}
        {requirements.length === 0 && !isLoading && (
            <p className="text-gray-500 text-center py-10">No requirements found. Upload documents to get started!</p>
        )}
      </div>
    </div>
  );
};

export default RequirementsDashboard;
