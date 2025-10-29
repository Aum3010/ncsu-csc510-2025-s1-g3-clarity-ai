import React, { useState, useEffect } from 'react';
import apiService from '../lib/api-service';
import LoadingSpinner from './LoadingSpinner';

const ClarificationPrompt = ({ term, onSubmit, onSkip }) => {
  const [clarifiedText, setClarifiedText] = useState('');
  const [action, setAction] = useState('replace');
  const [suggestions, setSuggestions] = useState([]);
  const [clarificationQuestion, setClarificationQuestion] = useState('');
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Load suggestions when term changes
    const loadSuggestions = async () => {
      if (!term?.id) return;

      setIsLoadingSuggestions(true);
      setError(null);

      try {
        const result = await apiService.getSuggestions(term.id);
        setSuggestions(result.suggestions || []);
        setClarificationQuestion(result.prompt || term.clarification_prompt || '');
      } catch (err) {
        console.error('Error loading suggestions:', err);
        setError('Failed to load suggestions');
        // Use fallback data from term if available
        setSuggestions(term.suggested_replacements || []);
        setClarificationQuestion(term.clarification_prompt || '');
      } finally {
        setIsLoadingSuggestions(false);
      }
    };

    loadSuggestions();
  }, [term]);

  const handleSuggestionClick = (suggestion) => {
    setClarifiedText(suggestion);
  };

  const handleSubmit = async () => {
    if (!clarifiedText.trim()) {
      setError('Please provide a clarification');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(clarifiedText, action);
    } catch (err) {
      console.error('Error submitting clarification:', err);
      setError(err.message || 'Failed to submit clarification');
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    onSkip();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-xl font-semibold text-gray-900">
                Clarify Ambiguous Term
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                Term: <span className="font-semibold text-orange-600">{term.term}</span>
              </p>
            </div>
            <button
              onClick={handleSkip}
              className="text-gray-400 hover:text-gray-600"
              disabled={isSubmitting}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Context */}
          {term.sentence_context && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600 mb-1 font-semibold">Context:</p>
              <p className="text-sm text-gray-700">{term.sentence_context}</p>
            </div>
          )}

          {/* Clarification question */}
          {clarificationQuestion && (
            <div className="mb-4">
              <p className="text-gray-800 font-medium">{clarificationQuestion}</p>
            </div>
          )}

          {/* AI Suggestions */}
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              AI-Generated Suggestions:
            </label>
            
            {isLoadingSuggestions ? (
              <div className="flex items-center justify-center py-4">
                <LoadingSpinner size="small" />
                <span className="ml-2 text-gray-600">Loading suggestions...</span>
              </div>
            ) : suggestions.length > 0 ? (
              <div className="space-y-2">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className={`w-full text-left p-3 rounded-lg border-2 transition-all duration-200 ${
                      clarifiedText === suggestion
                        ? 'border-orange-500 bg-orange-50'
                        : 'border-gray-200 hover:border-orange-300 bg-white'
                    }`}
                    disabled={isSubmitting}
                  >
                    <p className="text-gray-800">{suggestion}</p>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic">No suggestions available</p>
            )}
          </div>

          {/* Custom input */}
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Or provide your own clarification:
            </label>
            <textarea
              value={clarifiedText}
              onChange={(e) => setClarifiedText(e.target.value)}
              placeholder="Enter a more specific, quantifiable description..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          {/* Action selection */}
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              How should we apply this clarification?
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="replace"
                  checked={action === 'replace'}
                  onChange={(e) => setAction(e.target.value)}
                  className="mr-2 text-orange-500 focus:ring-orange-500"
                  disabled={isSubmitting}
                />
                <span className="text-gray-700">
                  Replace the ambiguous term with the clarification
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="append"
                  checked={action === 'append'}
                  onChange={(e) => setAction(e.target.value)}
                  className="mr-2 text-orange-500 focus:ring-orange-500"
                  disabled={isSubmitting}
                />
                <span className="text-gray-700">
                  Append the clarification to the requirement
                </span>
              </label>
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !clarifiedText.trim()}
              className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <LoadingSpinner size="small" />
                  <span>Submitting...</span>
                </>
              ) : (
                'Submit Clarification'
              )}
            </button>
            <button
              onClick={handleSkip}
              disabled={isSubmitting}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors duration-200"
            >
              Skip
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClarificationPrompt;
