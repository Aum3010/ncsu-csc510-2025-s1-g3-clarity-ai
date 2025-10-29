import React, { useState } from 'react';

const AmbiguityHighlighter = ({ text, ambiguousTerms, onTermClick }) => {
  const [hoveredTerm, setHoveredTerm] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  // Sort terms by position to process them in order
  const sortedTerms = [...(ambiguousTerms || [])].sort(
    (a, b) => a.position_start - b.position_start
  );

  // Get color based on confidence level and status
  const getHighlightColor = (term) => {
    if (term.status === 'clarified') {
      return 'bg-green-200 hover:bg-green-300 line-through';
    }
    
    const confidence = term.confidence || 0;
    if (confidence >= 0.8) {
      return 'bg-red-200 hover:bg-red-300';
    } else if (confidence >= 0.5) {
      return 'bg-yellow-200 hover:bg-yellow-300';
    } else {
      return 'bg-orange-200 hover:bg-orange-300';
    }
  };

  // Build highlighted text with spans
  const buildHighlightedText = () => {
    if (!text || sortedTerms.length === 0) {
      return <span className="whitespace-pre-line">{text}</span>;
    }

    const elements = [];
    let lastIndex = 0;

    sortedTerms.forEach((term, idx) => {
      const start = term.position_start;
      const end = term.position_end;

      // Add text before the term
      if (start > lastIndex) {
        elements.push(
          <span key={`text-${idx}`} className="whitespace-pre-line">
            {text.substring(lastIndex, start)}
          </span>
        );
      }

      // Add highlighted term
      const termText = text.substring(start, end);
      const colorClass = getHighlightColor(term);
      
      elements.push(
        <span
          key={`term-${idx}`}
          className={`${colorClass} cursor-pointer rounded px-1 transition-colors duration-150 relative`}
          onClick={() => term.status !== 'clarified' && onTermClick && onTermClick(term)}
          onMouseEnter={(e) => {
            setHoveredTerm(term);
            const rect = e.target.getBoundingClientRect();
            setTooltipPosition({
              x: rect.left + rect.width / 2,
              y: rect.top - 10,
            });
          }}
          onMouseLeave={() => setHoveredTerm(null)}
        >
          {termText}
        </span>
      );

      lastIndex = end;
    });

    // Add remaining text
    if (lastIndex < text.length) {
      elements.push(
        <span key="text-end" className="whitespace-pre-line">
          {text.substring(lastIndex)}
        </span>
      );
    }

    return elements;
  };

  return (
    <div className="relative">
      <div className="bg-white border border-gray-200 rounded-lg p-4 text-gray-700">
        {buildHighlightedText()}
      </div>

      {/* Tooltip */}
      {hoveredTerm && (
        <div
          className="fixed z-50 bg-gray-900 text-white text-sm rounded-lg shadow-lg p-3 max-w-xs"
          style={{
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div className="space-y-2">
            <div>
              <span className="font-semibold">Term:</span> {hoveredTerm.term}
            </div>
            
            {hoveredTerm.confidence !== undefined && (
              <div>
                <span className="font-semibold">Confidence:</span>{' '}
                {(hoveredTerm.confidence * 100).toFixed(0)}%
              </div>
            )}
            
            {hoveredTerm.reasoning && (
              <div>
                <span className="font-semibold">Why flagged:</span>{' '}
                {hoveredTerm.reasoning}
              </div>
            )}
            
            {hoveredTerm.status === 'clarified' ? (
              <div className="text-green-300 font-semibold">✓ Clarified</div>
            ) : (
              <div className="text-orange-300 text-xs mt-2">
                Click to clarify this term
              </div>
            )}
          </div>
          
          {/* Tooltip arrow */}
          <div
            className="absolute left-1/2 bottom-0 transform -translate-x-1/2 translate-y-full"
            style={{
              width: 0,
              height: 0,
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderTop: '6px solid #1f2937',
            }}
          />
        </div>
      )}

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-600">
        <div className="flex items-center gap-1">
          <span className="inline-block w-4 h-4 bg-red-200 rounded"></span>
          <span>High confidence (80%+)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-4 h-4 bg-yellow-200 rounded"></span>
          <span>Medium confidence (50-80%)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-4 h-4 bg-orange-200 rounded"></span>
          <span>Low confidence (&lt;50%)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-4 h-4 bg-green-200 rounded"></span>
          <span>Clarified</span>
        </div>
      </div>
    </div>
  );
};

export default AmbiguityHighlighter;
