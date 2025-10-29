import React, { useState, useEffect, useRef } from 'react';
import Tag from './Tag';
import AmbiguityDetectionPanel from './AmbiguityDetectionPanel';

const RequirementCard = ({ requirement, enableRealTimeAnalysis = false }) => {
  const { req_id, title, description, status, priority, source_document_filename, tags } = requirement;
  const [isEditing, setIsEditing] = useState(false);
  const [editedDescription, setEditedDescription] = useState(description);
  const [shouldAnalyze, setShouldAnalyze] = useState(false);
  const debounceTimerRef = useRef(null);

  // Debounced analysis trigger on text changes
  useEffect(() => {
    if (!enableRealTimeAnalysis || !isEditing) {
      return;
    }

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer for 1 second debounce
    debounceTimerRef.current = setTimeout(() => {
      if (editedDescription && editedDescription.trim() !== description) {
        setShouldAnalyze(true);
      }
    }, 1000);

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [editedDescription, enableRealTimeAnalysis, isEditing, description]);

  const handleEditToggle = () => {
    setIsEditing(!isEditing);
    if (isEditing) {
      // Reset to original description when canceling edit
      setEditedDescription(description);
    }
  };

  const handleDescriptionChange = (e) => {
    setEditedDescription(e.target.value);
  };

  const handleAnalysisComplete = (analysis) => {
    setShouldAnalyze(false);
    // Analysis complete - could update UI state here if needed
  };

  const handleClarificationSubmit = (result) => {
    // Update the description with clarified text
    if (result.updated_requirement) {
      setEditedDescription(result.updated_requirement.description);
    }
  };

  return (
    // Card background is white, border changed to warm orange
    <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-orange-400 hover:shadow-orange-400/30 transition-shadow duration-300">
      <div className="flex justify-between items-start mb-3">
        <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
        <div className="flex items-center gap-2">
          <span className="text-orange-500 font-mono text-sm">{req_id}</span>
          {enableRealTimeAnalysis && (
            <button
              onClick={handleEditToggle}
              className="text-sm px-3 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
            >
              {isEditing ? 'Cancel' : 'Edit'}
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {/* Tags will manage their own colors */}
        <Tag name={status} type="status" />
        <Tag name={`${priority} Priority`} type="priority" />

        {tags.map(tag => (
          <Tag key={tag.name} name={tag.name} /> 
        ))}
      </div>

      {isEditing ? (
        <textarea
          value={editedDescription}
          onChange={handleDescriptionChange}
          className="w-full p-3 border border-gray-300 rounded-lg text-gray-700 mb-4 min-h-[120px] focus:outline-none focus:ring-2 focus:ring-orange-400"
          placeholder="Edit requirement description..."
        />
      ) : (
        <p className="text-gray-700 mb-4 whitespace-pre-line">{description}</p>
      )}

      <div className="text-sm text-gray-500 mb-4">
        <span className="font-semibold">Source:</span> {source_document_filename || 'N/A'}
      </div>

      {/* Ambiguity Detection Panel - always shown but with real-time trigger when editing */}
      <AmbiguityDetectionPanel
        requirement={{ ...requirement, description: editedDescription }}
        onAnalysisComplete={handleAnalysisComplete}
        onClarificationSubmit={handleClarificationSubmit}
        autoAnalyze={shouldAnalyze}
        enableRealTime={enableRealTimeAnalysis && isEditing}
      />
    </div>
  );
};

export default RequirementCard;