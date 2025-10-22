import React, { useState } from 'react';
import axios from 'axios';

const StudioModal = ({ isOpen, onClose, onAnalysisSuccess }) => {
    const [selectedFiles, setSelectedFiles] = useState([]); 
    const [uploadStatus, setUploadStatus] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [documentIds, setDocumentIds] = useState([]); 

    const [analysisType, setAnalysisType] = useState('requirements'); // New state: 'requirements' or 'summary'
    const [query, setQuery] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState('');

    if (!isOpen) return null;

    const handleClose = () => {
        // Reset state on close
        setSelectedFiles([]);
        setUploadStatus('');
        setDocumentIds([]);
        setQuery('');
        setAnalysisResult('');
        setIsUploading(false);
        setIsAnalyzing(false);
        onClose();
    };

    const handleFileChange = (event) => {
        setSelectedFiles(Array.from(event.target.files));
        setUploadStatus('');
        setAnalysisResult('');
        setDocumentIds([]);
    };

    const handleUpload = async () => {
        if (selectedFiles.length === 0) {
            setUploadStatus('Please select at least one file.');
            return;
        }

        setIsUploading(true);
        setUploadStatus(`Uploading ${selectedFiles.length} file(s)...`);
        
        let uploadedIds = [];

        try {
            for (const file of selectedFiles) {
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await axios.post('http://127.0.0.1:5000/api/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
                uploadedIds.push(response.data.id);
                setUploadStatus(`Uploaded ${uploadedIds.length}/${selectedFiles.length} file(s). Processing RAG...`);
            }
            
            setUploadStatus(`Success! Uploaded ${selectedFiles.length} files. IDs: ${uploadedIds.join(', ')}. Ready for analysis.`);
            setDocumentIds(uploadedIds);

        } catch (error) {
            console.error('Upload error:', error.response ? error.response.data : error.message);
            const errorMsg = error.response?.data?.error || 'Upload failed.';
            setUploadStatus(`Error: ${errorMsg}`);
        } finally {
            setIsUploading(false);
            setSelectedFiles([]);
        }
    };

    const handleAnalyze = async () => {
        if (documentIds.length === 0) {
            setAnalysisResult('No documents processed. Please upload files first.');
            return;
        }

        // --- Logic for single vs multi-document analysis ---
        let endpoint = '';
        let payload = {};
        let successMessage = '';
        
        // Summarization should only work on the first document for simplicity in V1
        const targetDocumentId = documentIds[0];

        if (analysisType === 'summary') {
            if (documentIds.length > 1) {
                setAnalysisResult('Summary generation is only supported for the first uploaded document in V1.');
                return;
            }
            endpoint = 'summarize';
            payload = { documentId: targetDocumentId };
            successMessage = 'Summary generated successfully.';
        } else { // analysisType === 'requirements'
            if (!query) {
                setAnalysisResult('Please enter a query for requirement generation.');
                return;
            }
            endpoint = 'analyze';
            payload = { query: query, documentId: targetDocumentId }; 
            successMessage = 'Requirements have been generated and saved.';
        }

        setIsAnalyzing(true);
        setAnalysisResult('Thinking...');

        try {
            const response = await axios.post(`http://127.0.0.1:5000/api/${endpoint}`, payload);
            
            // Display the appropriate result
            if (analysisType === 'summary') {
                setAnalysisResult(response.data.summary);
            } else {
                setAnalysisResult(response.data.answer);
            }
            
            // --- AUTO-REFRESH TRIGGER ---
            // Only trigger refresh if requirements were generated (saved to DB)
            if (analysisType === 'requirements' && onAnalysisSuccess) {
                onAnalysisSuccess();
            }
            // --------------------------

        } catch (error) {
            console.error('Analysis error:', error.response ? error.response.data : error.message);
            const errorMsg = error.response?.data?.error || 'Analysis failed.';
            setAnalysisResult(`Error: ${errorMsg}`);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const isGenerateDisabled = (documentIds.length === 0 || (analysisType === 'requirements' && !query) || isAnalyzing);

    return (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex justify-center items-center z-50 transition-opacity">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl h-5/6 flex flex-col text-gray-900">
                <div className="flex justify-between items-center p-6 border-b border-gray-200">
                    <h2 className="text-2xl font-bold text-purple-700">Clarity AI Studio</h2>
                    <button onClick={handleClose} className="text-gray-600 hover:text-gray-900 text-3xl font-light">
                        &times;
                    </button>
                </div>
                
                <div className="p-6 flex-1 overflow-y-auto space-y-6">
                    <div className="grid grid-cols-2 gap-6">
                        {/* LEFT COLUMN: UPLOAD */}
                        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 text-gray-900">
                            <h3 className="text-lg font-semibold mb-3 text-purple-600">1. Document Ingestion</h3>
                            <div className="flex flex-col gap-3">
                                <input 
                                    type="file" 
                                    multiple
                                    onChange={handleFileChange} 
                                    className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-100 file:text-purple-700 hover:file:bg-purple-200"
                                />
                                <button 
                                    onClick={handleUpload} 
                                    disabled={isUploading || selectedFiles.length === 0}
                                    className="bg-purple-500 hover:bg-purple-600 text-white py-2 rounded-lg disabled:opacity-50"
                                >
                                    {isUploading ? 'Processing...' : `Upload ${selectedFiles.length > 0 ? selectedFiles.length + ' File(s)' : 'File(s)'}`}
                                </button>
                                {documentIds.length > 0 && 
                                    <p className="text-sm text-green-600">Successfully processed {documentIds.length} file(s). IDs: {documentIds.join(', ')}</p>
                                }
                            </div>
                            {uploadStatus && <p className={`mt-3 text-sm ${documentIds.length > 0 ? 'text-green-600' : 'text-red-600'}`}>{uploadStatus}</p>}
                        </div>

                        {/* RIGHT COLUMN: ANALYSIS */}
                        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 text-gray-900">
                            <h3 className="text-lg font-semibold mb-3 text-purple-600">2. AI Analysis & Generation</h3>
                            
                            {/* Analysis Type Selector */}
                            <div className="flex space-x-2 mb-4">
                                <button
                                    onClick={() => setAnalysisType('requirements')}
                                    className={`px-4 py-1 text-sm rounded-full transition-colors ${analysisType === 'requirements' ? 'bg-orange-500 text-white font-semibold' : 'bg-gray-300 text-gray-700 hover:bg-gray-400'}`}
                                >
                                    Generate Requirements
                                </button>
                                <button
                                    onClick={() => setAnalysisType('summary')}
                                    className={`px-4 py-1 text-sm rounded-full transition-colors ${analysisType === 'summary' ? 'bg-orange-500 text-white font-semibold' : 'bg-gray-300 text-gray-700 hover:bg-gray-400'}`}
                                >
                                    Generate Summary
                                </button>
                            </div>
                            
                            {/* Input Area (Conditional based on type) */}
                            {analysisType === 'requirements' && (
                                <textarea
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="e.g., Generate user stories, acceptance criteria, and priority tags for the core feature set."
                                    rows="5"
                                    className="w-full p-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                                    disabled={documentIds.length === 0}
                                />
                            )}
                            {analysisType === 'summary' && (
                                <p className="text-gray-600 py-3">The AI will generate a summary, key decisions, and action items based on the uploaded document.</p>
                            )}

                            <button 
                                onClick={handleAnalyze} 
                                disabled={isGenerateDisabled}
                                className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-2 rounded-lg disabled:opacity-50 mt-3"
                            >
                                {isAnalyzing ? 'Analyzing...' : `Run ${analysisType === 'summary' ? 'Summary' : 'Generation'}`}
                            </button>
                        </div>
                    </div>
                    
                    {/* RESULTS SECTION */}
                    {analysisResult && (
                        <div className="mt-6 p-4 bg-purple-50 rounded-lg border border-purple-300">
                            <h4 className="font-semibold text-purple-700 mb-2">Analysis Result:</h4>
                            <pre className="whitespace-pre-wrap text-sm text-gray-800">{analysisResult}</pre>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
};

export default StudioModal;