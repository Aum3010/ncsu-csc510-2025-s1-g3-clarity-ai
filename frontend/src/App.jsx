import { useState, useEffect } from 'react'
import axios from 'axios' // Import axios
import './App.css'

function App() {
  const [message, setMessage] = useState('Loading...')

  useEffect(() => {
    // Try to fetch data from our Flask backend
    axios.get('http://127.0.0.1:5000/')
      .then(response => {
        setMessage(response.data)
      })
      .catch(error => {
        console.error("Error fetching data:", error)
        setMessage('Failed to fetch data from backend.')
      })
  }, []) // The empty array means this runs once on component mount

  return (
    <>
      <h1>Clarity AI Frontend</h1>
      <p>
        Message from backend: <strong>{message}</strong>
      </p>
    </>
  )
}

export default App