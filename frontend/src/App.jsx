import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [message, setMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage(''); // Clear previous messages
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage('Please select a file first.');
      return;
    }

    setIsUploading(true);
    setMessage('Uploading...');

    // Create a FormData object to send the file
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Make the POST request to our backend's /api/upload endpoint
      const response = await axios.post('http://127.0.0.1:5000/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // Handle success
      setMessage(`Success! File uploaded with ID: ${response.data.id}`);
      setSelectedFile(null); // Clear the file input

    } catch (error) {
      // Handle error
      console.error('Error uploading file:', error);
      const errorMsg = error.response?.data?.error || 'An unexpected error occurred.';
      setMessage(`Error: ${errorMsg}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Clarity AI</h1>
        <p>Upload a document for analysis (.txt, .md, .pdf, .docx, .json)</p>
        
        <div className="upload-container">
          <input type="file" onChange={handleFileChange} />
          <button onClick={handleUpload} disabled={isUploading || !selectedFile}>
            {isUploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>

        {message && <p className="message">{message}</p>}
      </header>
    </div>
  );
}

export default App;
