import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { Edit2, Trash2, AlertTriangle } from 'lucide-react';
import Tag from './Tag'; 
import AmbiguityDetectionPanel from './AmbiguityDetectionPanel';

/**
 * RequirementCard component displays a single requirement with its details.
 * It integrates ambiguity detection and visually flags contradiction conflicts.
 * * @param {object} props
 * @param {object} props.requirement The requirement object to display (id, req_id, title, description, tags, etc.).
 * @param {boolean} props.enableRealTimeAnalysis Flag to enable real-time ambiguity analysis when editing.
 * @param {boolean} props.isConflicting Flag indicating if this requirement is part of a contradiction.
 * @param {boolean} props.isSelected Optional flag to visually highlight the card (e.g., when viewing a conflict).
 * @param {function} props.onEdit Handler for editing the requirement (Placeholder for now).
 * @param {function} props.onDelete Handler for deleting the requirement (Placeholder for now).
 */
const RequirementCard = ({ 
  requirement, 
  enableRealTimeAnalysis = false,
  isConflicting = false, // New prop for contradiction flag
  isSelected = false,    // New prop for visual selection (e.g., from contradiction panel)
  onEdit, // Placeholder prop
  onDelete // Placeholder prop
}) => {
  const { req_id, title, description, status, priority, source_document_filename, tags } = requirement;
  const [isEditing, setIsEditing] = useState(false);
  const [editedDescription, setEditedDescription] = useState(description);
  const [shouldAnalyze, setShouldAnalyze] = useState(false);
  const debounceTimerRef = useRef(null);

  // Determine card styling based on status and conflict flag
  const statusColor = {
    'Draft': 'text-gray-500',
    'In Review': 'text-yellow-600',
    'Approved': 'text-green-600',
    'Implemented': 'text-indigo-600',
  };

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

  // Conditional styling for the card border and background
  const cardClasses = `
    bg-white rounded-xl shadow-lg p-6 transition-all duration-300 
    ${isSelected ? 'ring-4 ring-indigo-400 ring-offset-2' : ''}
    ${isConflicting 
        ? 'border-l-4 border-red-500 bg-red-50 hover:shadow-xl' 
        : 'border-l-4 border-transparent hover:shadow-md'}
  `;

  return (
    <div className={cardClasses}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center space-x-3 min-w-0">
            {/* Contradiction Warning Icon (Visible if isConflicting is true) */}
            {isConflicting && (
                <AlertTriangle 
                    className="w-5 h-5 text-red-600 flex-shrink-0 animate-pulse" 
                    title="This requirement conflicts with another." 
                />
            )}
            
            {/* Requirement Title and ID */}
            <h3 className={`text-xl font-semibold leading-tight ${isConflicting ? 'text-red-700' : 'text-gray-900'} truncate`}>
                {title}
            </h3>
            <span className="text-gray-500 font-mono text-sm ml-2">{req_id}</span>
        </div>
        
        <div className="flex items-center gap-2 flex-shrink-0">
          {enableRealTimeAnalysis && (
            <button
              onClick={handleEditToggle}
              className="text-sm px-3 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
              title={isEditing ? 'Cancel Editing' : 'Edit Description'}
            >
              {isEditing ? 'Cancel' : 'Edit'}
            </button>
          )}
           <button 
                onClick={() => onEdit(requirement.id)} 
                className="text-gray-500 hover:text-indigo-600 p-1 rounded-full transition-colors"
                title="Edit Requirement"
            >
                <Edit2 className="w-4 h-4" />
            </button>
            <button 
                onClick={() => onDelete(requirement.id)} 
                className="text-gray-500 hover:text-red-600 p-1 rounded-full transition-colors"
                title="Delete Requirement"
            >
                <Trash2 className="w-4 h-4" />
            </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {/* Tags will manage their own colors */}
        <Tag name={status} type="status" />
        <Tag name={`${priority} Priority`} type="priority" />

        {tags && tags.map(tag => (
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

// Add PropTypes for validation
RequirementCard.propTypes = {
    requirement: PropTypes.shape({
        id: PropTypes.number.isRequired,
        req_id: PropTypes.string.isRequired,
        title: PropTypes.string.isRequired,
        description: PropTypes.string,
        status: PropTypes.string,
        priority: PropTypes.string,
        source_document_filename: PropTypes.string,
        tags: PropTypes.arrayOf(PropTypes.object),
    }).isRequired,
    enableRealTimeAnalysis: PropTypes.bool,
    isConflicting: PropTypes.bool,
    isSelected: PropTypes.bool,
    onEdit: PropTypes.func.isRequired,
    onDelete: PropTypes.func.isRequired,
};

// Add default props
RequirementCard.defaultProps = {
    enableRealTimeAnalysis: false,
    isConflicting: false,
    isSelected: false,
    onEdit: () => console.log('Edit handler not provided'),
    onDelete: () => console.log('Delete handler not provided'),
};

export default RequirementCard;