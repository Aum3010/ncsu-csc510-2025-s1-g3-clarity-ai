import React, { useState } from 'react';
import apiService from '../lib/api-service';
import LoadingSpinner from './LoadingSpinner';

const AmbiguityReport = ({ analysisData, onExport }) => {
  const [sortBy, setSortBy] = useState('confidence'); // confidence, status, term
  const [filterStatus, setFilterStatus] = useState('all'); // all, pending, clarified, skipped
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState('md');

  if (!analysisData) {
    return null;
  }

  const { total_terms_flagged = 0, terms_resolved = 0, terms = [] } = analysisData;
  const pendingCount = terms.filter(t => t.status === 'pending').length;

  // Filter terms
  const filteredTerms = terms.filter(term => {
    if (filterStatus === 'all') return true;
    return term.status === filterStatus;
  });

  // Sort terms
  const sortedTerms = [...filteredTerms].sort((a, b) => {
    switch (sortBy) {
      case 'confidence':
        return (b.confidence || 0) - (a.confidence || 0);
      case 'status':
        return a.status.localeCompare(b.status);
      case 'term':
        return a.term.localeCompare(b.term);
      default:
        return 0;
    }
  });

  // Get status badge color
  const getStatusBadgeColor = (status) => {
    switch (status) {
      case 'clarified':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'skipped':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Get confidence badge color
  const getConfidenceBadgeColor = (confidence) => {
    if (confidence >= 0.8) {
      return 'bg-red-100 text-red-800';
    } else if (confidence >= 0.5) {
      return 'bg-yellow-100 text-yellow-800';
    } else {
      return 'bg-orange-100 text-orange-800';
    }
  };

  // Handle export
  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      const blob = await apiService.exportReport(
        [analysisData.requirement_id],
        exportFormat
      );

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ambiguity-report-${analysisData.requirement_id}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      if (onExport) {
        onExport(exportFormat);
      }
    } catch (err) {
      console.error('Export error:', err);
      alert('Failed to export report: ' + err.message);
    } finally {
      setIsExporting(false);
    }
  };

  const progressPercentage = total_terms_flagged > 0 
    ? (terms_resolved / total_terms_flagged) * 100 
    : 0;

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-semibold text-gray-900">Ambiguity Report</h3>
        
        <div className="flex items-center gap-2">
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            disabled={isExporting}
          >
            <option value="md">Markdown (.md)</option>
            <option value="txt">Text (.txt)</option>
          </select>
          
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
          >
            {isExporting ? (
              <>
                <LoadingSpinner size="small" />
                <span>Exporting...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Export</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-orange-50 rounded-lg p-4">
          <p className="text-sm text-gray-600 mb-1">Total Flagged</p>
          <p className="text-3xl font-bold text-orange-600">{total_terms_flagged}</p>
        </div>
        
        <div className="bg-green-50 rounded-lg p-4">
          <p className="text-sm text-gray-600 mb-1">Resolved</p>
          <p className="text-3xl font-bold text-green-600">{terms_resolved}</p>
        </div>
        
        <div className="bg-yellow-50 rounded-lg p-4">
          <p className="text-sm text-gray-600 mb-1">Pending</p>
          <p className="text-3xl font-bold text-yellow-600">{pendingCount}</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-700">Resolution Progress</span>
          <span className="text-sm text-gray-600">{progressPercentage.toFixed(0)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-orange-500 h-3 rounded-full transition-all duration-300"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Filters and Sorting */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div>
          <label className="text-sm font-semibold text-gray-700 mr-2">Filter:</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          >
            <option value="all">All ({terms.length})</option>
            <option value="pending">Pending ({pendingCount})</option>
            <option value="clarified">Clarified ({terms_resolved})</option>
            <option value="skipped">Skipped ({terms.filter(t => t.status === 'skipped').length})</option>
          </select>
        </div>
        
        <div>
          <label className="text-sm font-semibold text-gray-700 mr-2">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          >
            <option value="confidence">Confidence</option>
            <option value="status">Status</option>
            <option value="term">Term (A-Z)</option>
          </select>
        </div>
      </div>

      {/* Terms List */}
      <div className="space-y-3">
        {sortedTerms.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No terms found matching the current filter
          </div>
        ) : (
          sortedTerms.map((term, idx) => (
            <div
              key={term.id || idx}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow duration-200"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900">{term.term}</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadgeColor(term.status)}`}>
                    {term.status}
                  </span>
                  {term.confidence !== undefined && (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getConfidenceBadgeColor(term.confidence)}`}>
                      {(term.confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
              </div>
              
              {term.sentence_context && (
                <div className="mb-2">
                  <p className="text-sm text-gray-600">
                    <span className="font-semibold">Context:</span> {term.sentence_context}
                  </p>
                </div>
              )}
              
              {term.reasoning && (
                <div className="mb-2">
                  <p className="text-sm text-gray-600">
                    <span className="font-semibold">Reasoning:</span> {term.reasoning}
                  </p>
                </div>
              )}
              
              {term.suggested_replacements && term.suggested_replacements.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-1">Suggestions:</p>
                  <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                    {term.suggested_replacements.map((suggestion, sIdx) => (
                      <li key={sIdx}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AmbiguityReport;
