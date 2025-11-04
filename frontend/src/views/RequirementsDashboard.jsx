import React, { useState, useEffect, useContext, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Settings, RefreshCw, AlertTriangle } from 'lucide-react';

// Assuming these are the existing imports (FIXED paths with explicit extensions)
import { getDocumentRequirements, deleteRequirement, updateRequirement } from '../lib/api-service.js'; 
import { runContradictionAnalysis, getLatestContradictionReport } from '../lib/api-service.js'; // NEW API functions (Fixed extension)
import { AuthContext } from '../lib/auth-context.jsx'; // Fixed extension
import LoadingSpinner from '../components/LoadingSpinner.jsx'; // Fixed extension
import RequirementCard from '../components/RequirementCard.jsx'; // Fixed extension
import Notification from '../components/Notification.jsx'; // Fixed extension
import ContradictionPanel from '../components/ContradictionPanel.jsx'; // Existing NEW Component

const RequirementsDashboard = () => {
    const { documentId } = useParams();
    const { user } = useContext(AuthContext);

    // Existing state for requirements
    const [requirements, setRequirements] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    
    // NEW state for Contradiction Analysis
    const [contradictionReport, setContradictionReport] = useState(null);
    const [isContradictionLoading, setIsContradictionLoading] = useState(false);
    // Stores the req_id strings (e.g., "R-101") that are part of the currently selected conflict pair(s)
    const [conflictingReqIds, setConflictingReqIds] = useState([]); 

    const fetchRequirements = useCallback(async () => {
        setIsLoading(true);
        try {
            // Note: This needs to be implemented to fetch requirements related to the documentId
            const data = await getDocumentRequirements(documentId);
            setRequirements(data.requirements || []);
        } catch (err) {
            setError('Failed to load requirements.');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, [documentId]);
    
    // NEW: Fetch latest contradiction report on initial load
    const fetchContradictionReport = useCallback(async () => {
        try {
            // Get the latest report saved in the DB
            const report = await getLatestContradictionReport(documentId);
            setContradictionReport(report);
            
            // Highlight all requirements involved in conflicts by default
            if (report && report.conflicts && report.conflicts.length > 0) {
                 const allConflictingIds = report.conflicts.flatMap(c => c.conflicting_requirement_ids);
                 setConflictingReqIds(Array.from(new Set(allConflictingIds)));
            }
        } catch (err) {
            // Assume 404/No report errors result in null
            // Check if the error object has a structure that indicates a missing report (e.g., specific status code or message)
            // Since we cannot inspect the error structure, we will rely on a basic check and suppress 404 logs.
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


    // Placeholder Handlers
    const handleEdit = (reqId) => {
        console.log('Editing requirement:', reqId);
        // Logic to open edit modal/form
    };
    const handleDelete = (reqId) => {
        console.log('Deleting requirement:', reqId);
        // Logic to open confirmation and delete
    };


    // NEW: Handler to trigger the analysis
    const handleRunContradictionAnalysis = async () => {
        setIsContradictionLoading(true);
        setError(null);
        try {
            // Run analysis and get the new report
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
    
    // NEW: Handler to set which conflict to highlight when a panel item is clicked
    const handleConflictSelect = (ids) => {
        setConflictingReqIds(ids);
        
        // Scroll to the first conflicting requirement to bring it into view
        const firstReqId = ids[0];
        // We use the req_id (e.g., R-101) for the DOM element ID
        const element = document.getElementById(`req-card-${firstReqId}`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    };

    // Utility function to check if a requirement is conflicting or selected
    const isRequirementConflicting = (reqId) => {
        // reqId here is the internal DB ID (number). We need the req_id (string, e.g., "R-101")
        const req_id = requirements.find(r => r.id === reqId)?.req_id;
        
        // Check if the formal req_id is in the conflicting list
        // Note: The RequirementCard uses isConflicting for *all* conflicts and isSelected for the currently focused conflict.
        // Since we are setting conflictingReqIds to the currently selected conflict pair(s), we use it for both for simplicity here.
        return req_id && conflictingReqIds.includes(req_id);
    };
    
    const isRequirementSelected = (reqId) => {
         const req_id = requirements.find(r => r.id === reqId)?.req_id;
         // In this dashboard implementation, isSelected is synonymous with being in the current conflictingReqIds list
         return req_id && conflictingReqIds.includes(req_id);
    };

    if (isLoading) {
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
                         {/* Contradiction Analysis Button */}
                         {isContradictionLoading ? (
                             <LoadingSpinner size="small" message="Analyzing..." />
                         ) : (
                             <button
                                 onClick={handleRunContradictionAnalysis}
                                 className="flex items-center px-4 py-2 bg-red-600 text-white font-semibold rounded-lg shadow-md hover:bg-red-700 transition duration-150 ease-in-out disabled:opacity-50"
                                 disabled={requirements.length === 0}
                                 title="Scan all requirements for logical conflicts"
                             >
                                 <AlertTriangle className="w-5 h-5 mr-2" />
                                 Analyze Contradictions
                             </button>
                         )}
                        {/* Refresh Button */}
                        <button 
                            onClick={fetchRequirements} 
                            className="flex items-center px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 transition duration-150 ease-in-out"
                        >
                            <RefreshCw className="w-5 h-5 mr-2" />
                            Refresh
                        </button>
                        <Settings className="w-6 h-6 text-gray-500 hover:text-gray-700 cursor-pointer" />
                    </div>
                </div>

                {/* Requirements List */}
                {requirements.length === 0 ? (
                    <div className="text-center p-10 border rounded-xl bg-gray-50">
                        <p className="text-lg text-gray-600">No requirements found for this document.</p>
                        <p className="text-sm text-gray-400 mt-2">Upload a file or generate new requirements to begin analysis.</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {requirements.map(req => (
                            // Use req.req_id (e.g., "R-101") for the DOM element ID
                            <div key={req.id} id={`req-card-${req.req_id}`}>
                                <RequirementCard
                                    requirement={req}
                                    // isConflicting flag is set to true if the req is part of the *overall* report
                                    isConflicting={contradictionReport?.conflicts?.some(c => c.conflicting_requirement_ids.includes(req.req_id)) || false}
                                    // isSelected flag is set if the req is part of the *currently selected* conflict in the panel
                                    isSelected={conflictingReqIds.includes(req.req_id)} 
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
                        <AlertTriangle className="w-5 h-5 mr-2" /> Contradictions Found
                    </h3>
                    <ContradictionPanel 
                        report={contradictionReport} 
                        onConflictSelect={handleConflictSelect} 
                        currentConflictingIds={conflictingReqIds} // Pass currently selected IDs for highlight logic
                        isLoading={isContradictionLoading}
                    />
                </div>

                {/* Placeholder for Ambiguity Analysis Section */}
                <div className="mb-6 pt-4 border-t border-gray-300">
                    <h3 className="font-bold text-lg text-indigo-700 mb-3">
                        Ambiguity Detection
                    </h3>
                    <div className="p-4 bg-white rounded-lg border text-sm text-gray-500">
                        Ambiguity report goes here (using existing components).
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RequirementsDashboard;
