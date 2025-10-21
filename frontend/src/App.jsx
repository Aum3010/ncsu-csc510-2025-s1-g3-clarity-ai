import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  // State for the upload section
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [documentId, setDocumentId] = useState(null);

  // State for the analysis section
  const [query, setQuery] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState('');

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setUploadMessage('');
    setAnalysisResult('');
    setDocumentId(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadMessage('Please select a file first.');
      return;
    }

    setIsUploading(true);
    setUploadMessage('Uploading & Processing...');
    setDocumentId(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post('http://127.0.0.1:5000/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      setUploadMessage(`Success! File uploaded with ID: ${response.data.id}`);
      setDocumentId(response.data.id); // Save the document ID for analysis
      setSelectedFile(null); 

    } catch (error) {
      console.error('Error uploading file:', error);
      const errorMsg = error.response?.data?.error || 'An unexpected error occurred.';
      setUploadMessage(`Error: ${errorMsg}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!query || !documentId) {
      setAnalysisResult('Please enter a query and upload a document first.');
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
      console.error('Error analyzing document:', error);
      const errorMsg = error.response?.data?.error || 'An unexpected error occurred.';
      setAnalysisResult(`Error: ${errorMsg}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Clarity AI</h1>
        <p>Upload a document for analysis (.txt, .md, .pdf, .docx, .json)</p>
        
        <div className="card">
          <h2>Step 1: Upload Document</h2>
          <div className="upload-container">
            <input type="file" onChange={handleFileChange} key={selectedFile ? selectedFile.name : 'file-input'} />
            <button onClick={handleUpload} disabled={isUploading || !selectedFile}>
              {isUploading ? 'Processing...' : 'Upload'}
            </button>
          </div>
          {uploadMessage && <p className="message">{uploadMessage}</p>}
        </div>

        {documentId && (
          <div className="card">
            <h2>Step 2: Analyze Document</h2>
            <p>Document ID: {documentId} is ready for analysis.</p>
            <div className="analysis-container">
              <input 
                type="text" 
                value={query} 
                onChange={(e) => setQuery(e.target.value)} 
                placeholder="e.g., Generate user stories for this feature"
              />
              <button onClick={handleAnalyze} disabled={isAnalyzing || !query}>
                {isAnalyzing ? 'Analyzing...' : 'Analyze Document'}
              </button>
            </div>
            {analysisResult && <p className="message">{analysisResult}</p>}
          </div>
        )}

      </header>
    </div>
  );
}

export default App;