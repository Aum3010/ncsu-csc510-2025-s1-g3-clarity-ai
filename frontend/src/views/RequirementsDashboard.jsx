import React, { useState, useEffect, useContext, useCallback, useRef } from 'react'; // Added 'useRef'
import { useParams } from 'react-router-dom';
import { Settings, RefreshCw, AlertTriangle } from 'lucide-react';

// --- API & Component Imports (Combined) ---
import { 
    getDocumentRequirements, 
    deleteRequirement, 
    updateRequirement,
    runContradictionAnalysis, 
    getLatestContradictionReport,
    batchAnalyzeRequirements // <-- This is the API from your 'main' branch
} from '../lib/api-service.js'; 
import { AuthContext } from '../lib/auth-context.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import RequirementCard from '../components/RequirementCard.jsx';
import Notification from '../components/Notification.jsx';
import ContradictionPanel from '../components/ContradictionPanel.jsx';

const RequirementsDashboard = () => {
    const { documentId } = useParams();
    const { user } = useContext(AuthContext);

    // === State for Requirements & Contradictions (from pranav_dev) ===
    const [requirements, setRequirements] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [contradictionReport, setContradictionReport] = useState(null);
    const [isContradictionLoading, setIsContradictionLoading] = useState(false);
    const [conflictingReqIds, setConflictingReqIds] = useState([]); 

    // === State for Ambiguity Analysis (Merged from main) ===
    const [enableRealTimeAnalysis, setEnableRealTimeAnalysis] = useState(false);
    const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false);
    const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 });
    const [batchResults, setBatchResults] = useState(null);
    const [showBatchResults, setShowBatchResults] = useState(false);
    const batchCancelRef = useRef(false);

    // === Core Data Fetching Functions ===
    const fetchRequirements = useCallback(async () => {
        setIsLoading(true);
        try {
            const data = await getDocumentRequirements(documentId);
            setRequirements(data.requirements || []);
        } catch (err) {
            setError('Failed to load requirements.');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, [documentId]);
    
    const fetchContradictionReport = useCallback(async () => {
        try {
            const report = await getLatestContradictionReport(documentId);
            setContradictionReport(report);
            
            if (report && report.conflicts && report.conflicts.length > 0) {
                 const allConflictingIds = report.conflicts.flatMap(c => c.conflicting_requirement_ids);
                 setConflictingReqIds(Array.from(new Set(allConflictingIds)));
            }
        } catch (err) {
            const isNotFoundError = err && err.message && err.message.includes('404');
            if (!isNotFoundError) {
                 console.error("Error fetching contradiction report:", err);
            }
            setContradictionReport(null);
            setConflictingReqIds([]);
        }
    }, [documentId]);

    // Initial data fetch
    useEffect(() => {
        if (documentId) {
            fetchRequirements();
            fetchContradictionReport();
        }
    }, [documentId, fetchRequirements, fetchContradictionReport]);


    // === Placeholder Handlers for Edit/Delete ===
    const handleEdit = (reqId) => {
        console.log('Editing requirement:', reqId);
    };
    const handleDelete = (reqId) => {
        console.log('Deleting requirement:', reqId);
    };


    // === Contradiction Analysis Handlers ===
    const handleRunContradictionAnalysis = async () => {
        setIsContradictionLoading(true);
        setError(null);
        try {
            const report = await runContradictionAnalysis(documentId, {}); 
            setContradictionReport(report);
            
            if (report && report.total_conflicts_found > 0) {
                 const allConflictingIds = report.conflicts.flatMap(c => c.conflicting_requirement_ids);
                 setConflictingReqIds(Array.from(new Set(allConflictingIds)));
                Notification.show('Contradiction analysis complete. Conflicts found!', 'error');
            } else {
                setConflictingReqIds([]);
                Notification.show('Analysis complete. No contradictions found.', 'success');
            }
        } catch (err) {
            setError(err.message || 'Failed to run contradiction analysis.');
        } finally {
            setIsContradictionLoading(false);
        }
    };
    
    const handleConflictSelect = (ids) => {
        setConflictingReqIds(ids);
        const firstReqId = ids[0];
        const element = document.getElementById(`req-card-${firstReqId}`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    };

    // === Ambiguity Analysis Handlers (Merged from main) ===
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
          const batchSize = 5; // From 'main'

          for (let i = 0; i < requirementIds.length; i += batchSize) {
            if (batchCancelRef.current) {
              setError("Batch analysis cancelled");
              break;
            }
            const batch = requirementIds.slice(i, i + batchSize);
            try {
              // This API function is from your 'main' branch logic
              const batchResults = await batchAnalyzeRequirements(batch); 
              results.push(...batchResults);
              setBatchProgress({ current: Math.min(i + batchSize, requirementIds.length), total: requirementIds.length });
              batchResults.forEach(result => {
                totalTerms += result.total_terms_flagged || 0;
                totalResolved += result.terms_resolved || 0;
              });
            } catch (err) {
              console.error(`Error analyzing batch ${i / batchSize + 1}:`, err);
            }
          }

          if (!batchCancelRef.current) {
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
        }
    };

    const handleCancelBatchAnalysis = () => {
        batchCancelRef.current = true;
    };


    // === RENDER LOGIC ===
    if (isLoading && requirements.length === 0) {
        return <LoadingSpinner message="Loading requirements..." />;
    }

    return (
        <div className="flex h-full overflow-hidden">
            
            {/* Main Content Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                
                {/* Dashboard Header and Controls */}
                <div className="flex justify-between items-center border-b pb-4 sticky top-0 bg-white z-10">
                    <h1 className="text-3xl font-extrabold text-gray-900">
                        Requirements Dashboard
                    </h1>
                    <div className="flex items-center space-x-3">
                         {/* Contradiction Button */}
                         {isContradictionLoading ? (
                             <LoadingSpinner size="small" message="Analyzing..." />
                         ) : (
                             <button
                                 onClick={handleRunContradictionAnalysis}
                                 className="flex items-center px-4 py-2 bg-red-600 text-white font-semibold rounded-lg shadow-md hover:bg-red-700 transition duration-150 ease-in-out disabled:opacity-50"
                                 disabled={requirements.length === 0 || isBatchAnalyzing}
                                 title="Scan all requirements for logical conflicts"
                             >
                                 <AlertTriangle className="w-5 h-5 mr-2" />
                                 Analyze Contradictions
                             </button>
                         )}

                        {/* Ambiguity Button (Merged from main) */}
                        <button
                            onClick={handleBatchAnalyze}
                            disabled={isBatchAnalyzing || isLoading || requirements.length === 0 || isContradictionLoading}
                            className="flex items-center px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg shadow-md hover:bg-purple-700 transition duration-150 ease-in-out disabled:opacity-50"
                            title="Analyze all requirements for ambiguity"
                        >
                            {isBatchAnalyzing ? 'Analyzing...' : '🔍 Analyze Ambiguity'}
                        </button>
                        
                        {/* Refresh Button */}
                        <button 
                            onClick={fetchRequirements} 
                            disabled={isBatchAnalyzing || isContradictionLoading}
                            className="flex items-center px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 transition duration-150 ease-in-out disabled:opacity-50"
                        >
                            <RefreshCw className="w-5 h-5 mr-2" />
                            Refresh
                        </button>
                        <Settings className="w-6 h-6 text-gray-500 hover:text-gray-700 cursor-pointer" />
                    </div>
                </div>

                {/* Error Banner */}
                {error && <div className="p-4 mb-4 text-center text-lg text-red-600 bg-red-100 rounded-lg">Error: {error}</div>}

                {/* Batch Ambiguity Analysis Progress (Merged from main) */}
                {isBatchAnalyzing && (
                  <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600"></div>
                        <span className="text-purple-900 font-semibold">
                          Analyzing for ambiguity... {batchProgress.current} / {batchProgress.total}
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

                {/* Batch Ambiguity Results (Merged from main) */}
                {showBatchResults && batchResults && (
                  <div className="mb-6 p-6 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-bold text-green-900">Ambiguity Analysis Complete</h3>
                      <button
                        onClick={() => setShowBatchResults(false)}
                        className="text-green-700 hover:text-green-900 text-2xl"
                      >
                        &times;
                      </button>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm text-gray-600 mb-1">Requirements Analyzed</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {batchResults.analyzedRequirements} / {batchResults.totalRequirements}
                        </p>
                      </div>
                      <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm text-gray-600 mb-1">Total Ambiguous Terms</p>
                        <p className="text-2xl font-bold text-orange-600">{batchResults.totalTerms}</p>
                      </div>
                      <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm text-gray-600 mb-1">Terms Resolved</p>
                        <p className="text-2xl font-bold text-green-600">{batchResults.totalResolved}</p>
                      </div>
                      <div className="bg-white p-4 rounded-lg shadow">
                        <p className="text-sm text-gray-600 mb-1">Pending Clarifications</p>
                        <p className="text-2xl font-bold text-purple-600">
                          {batchResults.totalTerms - batchResults.totalResolved}
                        </p>
                      </div>
                    </div>
                  </div>
                )}


                {/* Requirements List */}
                {requirements.length === 0 ? (
                    <div className="text-center p-10 border rounded-xl bg-gray-50">
                        <p className="text-lg text-gray-600">No requirements found for this document.</p>
                        <p className="text-sm text-gray-400 mt-2">Upload a file or generate new requirements to begin analysis.</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {requirements.map(req => (
                            <div key={req.id} id={`req-card-${req.req_id}`}>
                                <RequirementCard
                                    requirement={req}
                                    // Prop for Contradiction
                                    isConflicting={contradictionReport?.conflicts?.some(c => c.conflicting_requirement_ids.includes(req.req_id)) || false}
                                    // Prop for Contradiction
                                    isSelected={conflictingReqIds.includes(req.req_id)} 
                                    // Prop for Ambiguity (Merged from main)
                                    enableRealTimeAnalysis={enableRealTimeAnalysis}
                                    onEdit={handleEdit}
                                    onDelete={handleDelete}
                                />
                            </div>
                        ))}
                    </div>
                )}
            </div>
            
            {/* Analysis Sidebar Panel */}
            <div className="w-96 border-l border-gray-200 bg-gray-50 p-6 overflow-y-auto flex-shrink-0">
                <h2 className="text-xl font-bold text-gray-800 mb-4">Analysis Results</h2>
                
                {/* Contradiction Analysis Section */}
                <div className="mb-6">
                    <h3 className="font-bold text-lg text-red-700 mb-3 flex items-center">
                        <AlertTriangle className="w-5 h-5 mr-2" /> Contradictions
                    </h3>
                    <ContradictionPanel 
                        report={contradictionReport} 
                        onConflictSelect={handleConflictSelect} 
                        currentConflictingIds={conflictingReqIds}
                        isLoading={isContradictionLoading}
                    />
                </div>

                {/* Ambiguity Analysis Section (Merged from main) */}
                <div className="mb-6 pt-4 border-t border-gray-300">
                    <h3 className="font-bold text-lg text-indigo-700 mb-3">
                        Ambiguity Detection
                    </h3>
                    
                    {/* Real-time Toggle (Merged from main) */}
                    <div className="mb-4">
                        <button
                            onClick={() => setEnableRealTimeAnalysis(!enableRealTimeAnalysis)}
                            className={`w-full px-4 py-2 rounded-lg font-semibold transition-colors ${
                                enableRealTimeAnalysis
                                ? 'bg-orange-500 text-white hover:bg-orange-600'
                                : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                            }`}
                            title="Toggle real-time ambiguity analysis in the requirement cards"
                        >
                            {enableRealTimeAnalysis ? '⚡ Real-time ON' : '⚡ Real-time OFF'}
                        </button>
                    </div>

                    <div className="p-4 bg-white rounded-lg border text-sm text-gray-500">
                        Run "Analyze Ambiguity" to see a document-wide report.
                        <br /><br />
                        Toggle "Real-time" to check for ambiguity as you edit.
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RequirementsDashboard;