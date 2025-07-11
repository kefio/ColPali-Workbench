import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { Accordion, AccordionSummary, AccordionDetails, Typography, CircularProgress } from '@mui/material';
import ExpandMore from '@mui/icons-material/ExpandMore';
import axios from 'axios';

function SearchResult({ result }) {
  return (
    <div className="search-result-card">
      <h3>{result.title}</h3>
      <div className="result-details">
        <p>Pagina: {result.page}</p>
        <p>Rilevanza: {result.score.toFixed(2)}</p>
        <a href={result.url} target="_blank" rel="noopener noreferrer">Visualizza PDF</a>
      </div>
      {result.image && (
        <div className="result-image">
          <img src={`data:image/jpeg;base64,${result.image}`} alt="Preview" width="500px"/>
        </div>
      )}
    </div>
  );
}

function App() {
  const [loading, setLoading] = useState(false);
  const [searchTime, setSearchTime] = useState(null);
  const [uploadTime, setUploadTime] = useState(null);
  const [data, setData] = useState(null);
  const [query, setQuery] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfUrl, setPdfUrl] = useState('');
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);  // Define setError
  const [deployStatus, setDeployStatus] = useState(null); // Aggiungi stato per la spia del deploy
  const [deployLoading, setDeployLoading] = useState(false); // Aggiungi stato per lo spinner del deploy
  const fileInputRef = useRef(null); // Aggiungi useRef per l'input file

  useEffect(() => {
    // Function to fetch logs from the backend
    const fetchLogs = async () => {
      
      try {
        
        const response = await axios.get('http://localhost:8000/logs', {
          
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.data.logs) {
          setLogs(response.data.logs);
        }
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();

    // Optional: periodic log update
    const interval = setInterval(fetchLogs, 5000); // every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleClearLogs = async () => {
    if (window.confirm('Are you sure you want to clear all logs?')) {
      try {
        const response = await axios.delete('http://localhost:8000/clear_logs', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        if (response.data.status === 'success') {
          setLogs([]); // Clear logs in the interface
          alert('All logs have been cleared.');
        } else {
          alert('Error clearing logs.');
        }
      } catch (err) {
        setError(err);
        console.error('Error clearing logs:', err);
        alert('Error clearing logs.');
      }
    }
  };

  const handleSearch = () => {
    setLoading(true);
    setSearchTime(null); // Azzera il cronometro
    const startTime = Date.now();
    
    fetch('http://localhost:8000/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain',
      },
      body: query
    })
      .then(response => response.json())
      .then(data => {
        setData(data);
        setSearchTime((Date.now() - startTime) / 1000); // Time in seconds
      })
      .catch(error => console.error('Error searching:', error))
      .finally(() => setLoading(false));
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    setPdfFile(file);
  };

  const handleStartIndexing = () => {
    if (!pdfFile) {
      alert('Select a PDF file before proceeding');
      return;
    }

    setLoading(true);
    setUploadTime(null); // Azzera il cronometro
    const startTime = Date.now();
    const formData = new FormData();
    formData.append('file', pdfFile); // Changed from 'pdf' to 'file'

    fetch('http://localhost:8000/pdf', {
      method: 'POST',
      body: formData,
      // Remove the Content-Type header to allow the browser to automatically set
      // the correct boundary for multipart/form-data
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        setPdfUrl(data.url);
        setUploadTime((Date.now() - startTime) / 1000); // Tempo in secondi
        setPdfFile(null); // Svuota l'uploader del file
        fileInputRef.current.value = ''; // Imposta il valore dell'input file a una stringa vuota
        alert(`Caricamento effettuato con successo in ${((Date.now() - startTime) / 1000).toFixed(2)} secondi`);
      })
      .catch(error => {
        console.error('Error indexing:', error);
        alert('Error uploading the PDF file');
      })
      .finally(() => {
        setLoading(false); // Sposta setLoading(false) dopo l'alert
      });
  };

  const handleDeploy = async () => {
    setDeployLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/deploy', {}, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.status === 200) {
        setDeployStatus('success');
      } else {
        setDeployStatus('error');
      }
    } catch (error) {
      setDeployStatus('error');
    } finally {
      setDeployLoading(false);
    }
  };

  const formatDataWithoutImage = (data) => {
    if (!data) return null;
    const formattedData = { ...data };
    if (formattedData.results) {
      formattedData.results = formattedData.results.map(result => ({
        ...result,
        image: result.image ? '[BASE64_IMAGE_DATA]' : null
      }));
    }
    return formattedData;
  };

  return (
    <div className="App">
      <nav className="App-nav">
        <div className="nav-content">
          <h1>SylloColPali</h1>
          {loading && <CircularProgress size={30} thickness={4} className="nav-spinner" />}
          <div className="deploy-container">
            <button onClick={handleDeploy} className="deploy-button">
              Deploy App on Vespa
              <span className={`deploy-status ${deployStatus}`}></span>
            </button>
            {deployLoading && <CircularProgress size={20} thickness={4} className="deploy-spinner" />}
          </div>
        </div>
      </nav>
      <main className="App-header">
        <div className="App-left-panel">
          <div className="App-section">
            <div className="section-header">
              <h2>Upload PDF</h2>
              {uploadTime && <span className="timer">Time: {uploadTime.toFixed(2)}s</span>}
            </div>
            <input
              ref={fileInputRef} // Aggiungi ref all'input file
              type="file"
              accept="application/pdf"
              onChange={handleFileUpload}
            />
            <button onClick={handleStartIndexing}>Index</button>
            {pdfUrl && (
              <div className="upload-result">
                <p>PDF uploaded: <a href={pdfUrl} target="_blank" rel="noopener noreferrer">View PDF</a></p>
              </div>
            )}
          </div>
          <div className="App-section">
            <div className="section-header">
              <h2>Search</h2>
              {searchTime && <span className="timer">Time: {searchTime.toFixed(2)}s</span>}
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search"
            />
            <button onClick={handleSearch}>Search</button>
          </div>
        </div>
        
        <div className="App-right-panel">
          {data && data.llama_response && (
            <div className="llama-response">
              <h3>LLama Response</h3>
              <p>{data.llama_response}</p>
            </div>
          )}

          <Accordion defaultExpanded>
            <AccordionSummary
              expandIcon={<ExpandMore />}
              aria-controls="formatted-results-content"
              id="formatted-results-header"
            >
              <Typography>Formatted Results</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {data && data.results ? (
                <div className="search-results-list">
                  {data.results.map((result, index) => (
                    <SearchResult key={index} result={result} />
                  ))}
                </div>
              ) : (
                <p className="no-results">No results to display</p>
              )}
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary
              expandIcon={<ExpandMore />}
              aria-controls="json-results-content"
              id="json-results-header"
            >
              <Typography>JSON Results</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {data ? (
                <pre>{JSON.stringify(formatDataWithoutImage(data), null, 2)}</pre>
              ) : (
                <p className="no-results">No results to display</p>
              )}
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary
              expandIcon={<ExpandMore />}
              aria-controls="logs-content"
              id="logs-header"
            >
              <Typography>Server Logs</Typography>
              <button onClick={handleClearLogs} style={{ marginLeft: 'auto' }}>Clear Logs</button>
            </AccordionSummary>
            <AccordionDetails>
              <div className="log-container">
                <pre style={{ backgroundColor: '#000', padding: '5px', maxHeight: '500px', overflowY: 'scroll', marginTop: '0px' }}>
                  {logs.join('')}
                </pre>
              </div>
            </AccordionDetails>
          </Accordion>
        </div>
      </main>
    </div>
  );
}

export default App;