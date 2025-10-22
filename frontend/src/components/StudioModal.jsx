import React, { useState } from 'react';
import axios from 'axios';

const StudioModal = ({ isOpen, onClose }) => {
    // State for the upload section
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploadStatus, setUploadStatus] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [documentId, setDocumentId] = useState(null);

    // State for the analysis section
    const [query, setQuery] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState('');

    if (!isOpen) return null;

    // Reset all state when the modal is closed
    const handleClose = () => {
        setSelectedFile(null);
        setUploadStatus('');
        setDocumentId(null);
        setQuery('');
        setAnalysisResult('');
        setIsUploading(false);
        setIsAnalyzing(false);
        onClose();
    };

    const handleFileChange = (event) => {
        setSelectedFile(event.target.files[0]);
        setUploadStatus('');
        setAnalysisResult('');
        setDocumentId(null);
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            setUploadStatus('Please select a file first.');
            return;
        }

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            setIsUploading(true);
            setUploadStatus('Uploading & Processing RAG Pipeline...');
            
            const response = await axios.post('http://127.0.0.1:5000/api/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            
            setUploadStatus(`Success! File uploaded with ID: ${response.data.id}. Ready for analysis.`);
            setDocumentId(response.data.id);

        } catch (error) {
            console.error('Upload error:', error.response ? error.response.data : error.message);
            const errorMsg = error.response?.data?.error || 'Upload failed.';
            setUploadStatus(`Error: ${errorMsg}`);
        } finally {
            setIsUploading(false);
            setSelectedFile(null);
        }
    };

    const handleAnalyze = async () => {
        if (!query || !documentId) {
            setAnalysisResult('Missing query or document ID.');
            return;
        }

        setIsAnalyzing(true);
        setAnalysisResult('Thinking...');

        try {
            const response = await axios.post('http://127.0.0.1:5000/api/analyze', {
                query: query,
                documentId: documentId,
            });

            setAnalysisResult(response.data.answer); 

        } catch (error) {
            console.error('Analysis error:', error.response ? error.response.data : error.message);
            const errorMsg = error.response?.data?.error || 'Analysis failed.';
            setAnalysisResult(`Error: ${errorMsg}`);
        } finally {
            setIsAnalyzing(false);
        }
    };


    return (
        // Modal background remains semi-dark for focus
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex justify-center items-center z-50 transition-opacity">
            {/* Modal content background is bright white */}
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
                        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                            <h3 className="text-lg font-semibold mb-3 text-purple-600">1. Document Ingestion</h3>
                            <div className="flex flex-col gap-3">
                                <input 
                                    type="file" 
                                    onChange={handleFileChange} 
                                    className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-100 file:text-purple-700 hover:file:bg-purple-200"
                                />
                                <button 
                                    onClick={handleUpload} 
                                    disabled={isUploading || !selectedFile}
                                    className="bg-purple-500 hover:bg-purple-600 text-white py-2 rounded-lg disabled:opacity-50"
                                >
                                    {isUploading ? 'Processing...' : 'Upload & Process RAG'}
                                </button>
                            </div>
                            {uploadStatus && <p className={`mt-3 text-sm ${documentId ? 'text-green-600' : 'text-red-600'}`}>{uploadStatus}</p>}
                        </div>

                        {/* RIGHT COLUMN: ANALYSIS */}
                        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                            <h3 className="text-lg font-semibold mb-3 text-purple-600">2. AI Analysis & Generation</h3>
                            <div className="flex flex-col gap-3">
                                <textarea
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="e.g., Generate user stories, acceptance criteria, and priority tags for the core feature set."
                                    rows="5"
                                    className="w-full p-2 bg-white border border-gray-300 rounded-lg text-gray-900"
                                    disabled={!documentId}
                                />
                                <button 
                                    onClick={handleAnalyze} 
                                    disabled={isAnalyzing || !documentId || !query}
                                    className="bg-orange-500 hover:bg-orange-600 text-white font-bold py-2 rounded-lg disabled:opacity-50"
                                >
                                    {isAnalyzing ? 'Analyzing...' : 'Generate Requirements'}
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    {/* RESULTS SECTION */}
                    {analysisResult && (
                        <div className="mt-6 p-4 bg-purple-50 rounded-lg border border-purple-300">
                            <h4 className="font-semibold text-purple-700 mb-2">Analysis Status:</h4>
                            <pre className="whitespace-pre-wrap text-sm text-gray-800">{analysisResult}</pre>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
};

export default StudioModal;