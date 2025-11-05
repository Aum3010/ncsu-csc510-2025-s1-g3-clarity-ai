import React from 'react';
import PropTypes from 'prop-types';
const SimpleSpinner = () => (
  <div className="flex items-center justify-center">
    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-600 mr-3"></div>
    <span className="font-semibold">Analyzing...</span>
  </div>
);

/**
 * ContradictionPanel component displays the results of the LLM's contradiction analysis.
 * It lists each conflicting pair found and explains the reason for the conflict.
 * It also displays the overall status of the analysis.
 *
 * @param {object} props - The component props.
 * @param {object | null} props.report - The latest ContradictionAnalysis report object.
 * @param {function} props.onConflictSelect - Handler when a conflict is selected (e.g., to highlight requirements).
 * @param {boolean} props.isLoading - Flag to show a loading state.
 */
const ContradictionPanel = ({ report, onConflictSelect, isLoading }) => {
    
    if (isLoading) {
        return (
            <div className="p-4 bg-white border border-gray-200 text-gray-700 rounded-lg shadow-sm flex items-center justify-center">
                <SimpleSpinner />
            </div>
        );
    }

    if (!report || report.status === 'no_conflicts') {
        return (
            <div className="p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg shadow-sm">
                <div className="flex items-center">
                    <span className="w-5 h-5 mr-2" role="img" aria-label="check">✅</span>
                    <span className="font-semibold">No Contradictions Found</span>
                </div>
                <p className="text-sm mt-1">The analysis found no logical inconsistencies in your requirements.</p>
            </div>
        );
    }

    if (report.status === 'pending') {
        return (
            <div className="p-4 bg-yellow-50 border border-yellow-200 text-yellow-700 rounded-lg shadow-sm animate-pulse">
                <div className="flex items-center">
                    <span className="w-5 h-5 mr-2" role="img" aria-label="warning">⚠️</span>
                    <span className="font-semibold">Analysis Pending...</span>
                </div>
                <p className="text-sm mt-1">Please wait, the logic auditor is scanning your requirements for conflicts.</p>
            </div>
        );
    }
    
    // Assume report.status is 'complete' and report.conflicts list is present
    const unresolvedConflicts = report.conflicts ? report.conflicts.filter(c => c.status !== 'resolved') : [];

    // --- UPDATED: Handle case where analysis is complete but no conflicts are found ---
    if (unresolvedConflicts.length === 0) {
         return (
            <div className="p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg shadow-sm">
                <div className="flex items-center">
                    <span className="w-5 h-5 mr-2" role="img" aria-label="check">✅</span>
                    <span className="font-semibold">Analysis Complete</span>
                </div>
                <p className="text-sm mt-1">No logical inconsistencies were found.</p>
            </div>
        );
    }
    // --- End Update ---

    return (
        <div className="bg-white border border-red-300 rounded-xl shadow-lg p-4 h-full flex flex-col">
            <h3 className="flex items-center text-lg font-bold text-red-700 mb-3 border-b pb-2">
                <span className="w-6 h-6 mr-2 flex-shrink-0" role="img" aria-label="error">❌</span>
                {unresolvedConflicts.length} Critical Contradictions Found
            </h3>
            
            <div className="space-y-4 overflow-y-auto">
                {unresolvedConflicts.map((conflict, index) => (
                    <div 
                        key={conflict.id} 
                        className={`p-3 border-l-4 rounded-lg cursor-pointer transition-all ${
                            conflict.status === 'pending' 
                            ? 'bg-red-50 border-red-500 hover:bg-red-100' 
                            : 'bg-gray-100 border-gray-400'
                        }`}
                        onClick={() => onConflictSelect(conflict.conflicting_requirement_ids)}
                    >
                        <div className="font-semibold text-sm text-red-800 flex justify-between items-center">
                            <span>Conflict {index + 1}: {conflict.conflict_id}</span>
                            <span className="text-xs font-medium text-red-600 bg-red-200 px-2 py-0.5 rounded-full">
                                {conflict.status.toUpperCase()}
                            </span>
                        </div>
                        <p className="text-xs text-gray-700 mt-1 italic">
                            Reason: {conflict.reason}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                            Conflicting IDs: <span className="font-mono text-red-700">{conflict.conflicting_requirement_ids.join(', ')}</span>
                        </p>
                        <div className="mt-2 text-right">
                             {/* In a real app, this would be a button to mark as resolved */}
                            <button className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                                View Details &rarr;
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {unresolvedConflicts.length > 0 && (
                <div className="mt-4 pt-3 border-t text-xs text-gray-500 text-center">
                    Click on a conflict to jump to the requirements.
                </div>
            )}
        </div>
    );
};

ContradictionPanel.propTypes = {
    report: PropTypes.shape({
        id: PropTypes.number,
        analyzed_at: PropTypes.string,
        total_conflicts_found: PropTypes.number,
        status: PropTypes.string,
        conflicts: PropTypes.arrayOf(PropTypes.shape({
            id: PropTypes.number,
            conflict_id: PropTypes.string,
            reason: PropTypes.string,
            conflicting_requirement_ids: PropTypes.arrayOf(PropTypes.string),
            status: PropTypes.string,
        })),
    }),
    onConflictSelect: PropTypes.func.isRequired,
    isLoading: PropTypes.bool, 
};

ContradictionPanel.defaultProps = {
    isLoading: false,
    report: null, 
};

export default ContradictionPanel;