import React, { useState, useEffect } from 'react';
import { Box, Button, Typography, CircularProgress, Paper, TextField } from '@mui/material';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://scare-unified-dash-production.up.railway.app';

const CorsTest = () => {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [apiUrl, setApiUrl] = useState(API_BASE_URL);

  const testEndpoints = [
    '/api/health',
    '/api/campaigns/metrics',
    '/api/campaign-mappings'
  ];

  const addResult = (endpoint, method, success, message, headers) => {
    const timestamp = new Date().toLocaleTimeString();
    setResults(prev => [
      { endpoint, method, success, message, headers, timestamp },
      ...prev
    ]);
  };

  const testCors = async () => {
    setLoading(true);
    setResults([]);

    // Test all endpoints
    for (const endpoint of testEndpoints) {
      const url = `${apiUrl}${endpoint}`;
      
      // Test with fetch without credentials
      try {
        console.log(`Testing fetch (no credentials) to ${url}`);
        const fetchResponse = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        // Log headers for debugging
        const headers = {};
        fetchResponse.headers.forEach((value, key) => {
          headers[key] = value;
        });
        
        console.log(`Response status: ${fetchResponse.status}`);
        console.log('Response headers:', headers);
        
        if (fetchResponse.ok) {
          addResult(endpoint, 'FETCH', true, `Status: ${fetchResponse.status}`, headers);
        } else {
          addResult(endpoint, 'FETCH', false, `Error: ${fetchResponse.status} ${fetchResponse.statusText}`, headers);
        }
      } catch (error) {
        console.error(`Error with fetch request to ${url}:`, error);
        addResult(endpoint, 'FETCH', false, `Error: ${error.message}`, {});
      }
      
      // Test with fetch with credentials
      try {
        console.log(`Testing fetch (with credentials) to ${url}`);
        const fetchResponseWithCreds = await fetch(url, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        // Log headers for debugging
        const headersWithCreds = {};
        fetchResponseWithCreds.headers.forEach((value, key) => {
          headersWithCreds[key] = value;
        });
        
        console.log(`Response status: ${fetchResponseWithCreds.status}`);
        console.log('Response headers:', headersWithCreds);
        
        if (fetchResponseWithCreds.ok) {
          addResult(endpoint, 'FETCH+CREDS', true, `Status: ${fetchResponseWithCreds.status}`, headersWithCreds);
        } else {
          addResult(endpoint, 'FETCH+CREDS', false, `Error: ${fetchResponseWithCreds.status} ${fetchResponseWithCreds.statusText}`, headersWithCreds);
        }
      } catch (error) {
        console.error(`Error with fetch request with credentials to ${url}:`, error);
        addResult(endpoint, 'FETCH+CREDS', false, `Error: ${error.message}`, {});
      }
    }
    
    setLoading(false);
  };

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>CORS Test Tool</Typography>
      
      <Box mb={3}>
        <TextField
          fullWidth
          label="API Base URL"
          variant="outlined"
          value={apiUrl}
          onChange={(e) => setApiUrl(e.target.value)}
          margin="normal"
        />
        <Button
          variant="contained"
          color="primary"
          onClick={testCors}
          disabled={loading}
          sx={{ mt: 2, mb: 2 }}
        >
          {loading ? <CircularProgress size={24} color="inherit" /> : 'Test CORS'}
        </Button>
      </Box>
      
      {results.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>Test Results</Typography>
          {results.map((result, index) => (
            <Paper key={index} elevation={2} sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle1" color={result.success ? 'success.main' : 'error.main'} fontWeight="bold">
                {result.success ? '✅ Success' : '❌ Failed'} - {result.method}
              </Typography>
              <Typography variant="body2">
                Endpoint: {result.endpoint}
              </Typography>
              <Typography variant="body2">
                {result.message}
              </Typography>
              <Typography variant="body2" fontStyle="italic" color="text.secondary">
                Time: {result.timestamp}
              </Typography>
              <Typography variant="subtitle2" mt={1}>
                Response Headers:
              </Typography>
              <Box sx={{ backgroundColor: '#f5f5f5', p: 1, borderRadius: 1, maxHeight: '150px', overflow: 'auto' }}>
                <pre style={{ margin: 0 }}>
                  {JSON.stringify(result.headers, null, 2)}
                </pre>
              </Box>
            </Paper>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default CorsTest;
