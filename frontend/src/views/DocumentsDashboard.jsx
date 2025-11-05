import React, { useState, useEffect } from 'react';
import apiService from '../lib/api-service.js';

const DocumentsDashboard = ({ onTriggerRefresh }) => {
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadError, setUploadError] = useState('');

  // --- New state for delete confirmation modal ---
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null); // { id, filename }

  const fetchDocuments = async () => {
    try {
      setIsLoadingDocs(true);
      const response = await apiService.coreApi('/api/documents');
      
      // The API returns the array directly, not nested under a 'documents' key.
      setDocuments(response); 

    } catch (err) {
      console.error("Error fetching documents:", err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      if (!isMounted) return;
      await fetchDocuments();
    };
    
    loadData();
    
    return () => {
      isMounted = false;
    };
  }, []);

  const handleFileChange = (event) => {
    setSelectedFiles(Array.from(event.target.files));
    setUploadStatus('');
    setUploadError('');
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setUploadError('Please select at least one file.');
      return;
    }

    setIsUploading(true);
    setUploadStatus(`Uploading ${selectedFiles.length} file(s)...`);
    
    try {
      for (const file of selectedFiles) {
        const formData = new FormData();
        formData.append('file', file);
        
        await apiService.coreApi('/api/upload', {
          method: 'POST',
          body: formData,
          headers: {} // Let the browser set Content-Type for FormData
        });
      }
      
      setUploadStatus(`Success! Uploaded ${selectedFiles.length} files.`);
      setSelectedFiles([]); // Clear selection
      // Reset the file input field so the same file can be re-uploaded
      document.getElementById('file-input').value = null; 
      
      onTriggerRefresh(); 
      fetchDocuments();

    } catch (error) {
      console.error('Upload error:', error.response ? error.response.data : error.message);
      const errorMsg = error.response?.data?.error || 'Upload failed.';
      setUploadError(`Error: ${errorMsg}`);
    } finally {
      setIsUploading(false);
    }
  };

  // --- Updated Delete Flow ---
  // 1. Show the confirmation modal
  const promptDelete = (doc) => {
    setDocToDelete(doc);
    setShowDeleteModal(true);
  };

  // 2. Handle the actual deletion
  const handleDelete = async () => {
    if (!docToDelete) return;

    try {
      await apiService.coreApi(`/api/documents/${docToDelete.id}`, { method: 'DELETE' });
      onTriggerRefresh();
      fetchDocuments();
    } catch (error) {
      console.error('Delete error:', error.response ? error.response.data : error.message);
      setUploadError('Error deleting file. Please try again.'); // Show error in UI
    } finally {
      // Close the modal
      setShowDeleteModal(false);
      setDocToDelete(null);
    }
  };


  return (
    <>
      <div className="flex-1 p-8 text-gray-900">
        <h2 className="text-3xl font-bold text-gray-900 mb-8">Document Management</h2>

        {/* Upload Section */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-8 border-l-4 border-blue-400">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Upload New Documents</h3>
          <p className="text-gray-600 mb-4">Files uploaded here are automatically processed and added to the AI's knowledge base (RAG).</p>
          <div className="flex flex-col gap-3">
              <input 
                  id="file-input"
                  type="file" 
                  multiple
                  onChange={handleFileChange} 
                  className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200"
              />
              <button 
                  onClick={handleUpload} 
                  disabled={isUploading || selectedFiles.length === 0}
                  className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-lg disabled:opacity-50 w-full md:w-auto self-start font-semibold transition-colors duration-200"
              >
                  {isUploading ? 'Processing...' : `Upload ${selectedFiles.length > 0 ? selectedFiles.length + ' File(s)' : ''}`}
              </button>
              {uploadStatus && <p className="text-sm text-green-600">{uploadStatus}</p>}
              {uploadError && <p className="text-sm text-red-600">{uploadError}</p>}
          </div>
        </div>

        {/* Document List Section */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Uploaded Documents</h3>
          {isLoadingDocs ? (
              <p>Loading documents...</p>
          ) : (
              <div className="space-y-3">
                  {documents.length > 0 ? documents.map(doc => (
                      <DocumentItem 
                        key={doc.id} 
                        doc={doc} 
                        onDelete={() => promptDelete(doc)} // Use promptDelete
                      />
                  )) : (
                      <p className="text-gray-500">No documents have been uploaded yet.</p>
                  )}
              </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex justify-center items-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <span className="text-red-500 mr-2 text-xl">⚠️</span>
                Confirm Deletion
              </h3>
              <button 
                onClick={() => setShowDeleteModal(false)} 
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                &times;
              </button>
            </div>
            <p className="text-gray-700 mb-6">
              Are you sure you want to delete "<strong>{docToDelete?.filename}</strong>"? This will permanently remove it and its associated data from the AI's knowledge.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="py-2 px-4 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold transition-colors duration-200"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="py-2 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold transition-colors duration-200"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};


const DocumentItem = ({ doc, onDelete }) => {
    
    // Format the date string
    const formattedDate = new Date(doc.created_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });

    return (
        <div className="flex justify-between items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors duration-150">
            <div className="flex items-center space-x-3">
                <span className="text-xl">📄</span>
                <div>
                    <p className="font-semibold text-gray-800">{doc.filename}</p>
                    <p className="text-sm text-gray-500">Uploaded on {formattedDate}</p>
                </div>
            </div>
            <div className='flex items-center space-x-3'>
              <button 
                  onClick={onDelete}
                  className="text-gray-400 hover:text-red-600 transition-colors duration-150 p-1 rounded-full font-mono text-sm"
                  title="Delete Document"
              >
                  (Delete)
              </button>
            </div>
        </div>
    );
};

export default DocumentsDashboard;