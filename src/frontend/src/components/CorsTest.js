import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Paper, CircularProgress, Alert } from '@mui/material';
import corsProxy from '../utils/corsProxy';

/**
 * Component to test CORS configuration
 */
const CorsTest = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const testCors = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Try to fetch from the CORS test endpoint
      const response = await corsProxy.get('/api/cors-test');
      setResult(response.data);
    } catch (err) {
      console.error('CORS test failed:', err);
      setError(err.message || 'Failed to connect to the API');
    } finally {
      setLoading(false);
    }
  };

  // Run the test on component mount
  useEffect(() => {
    testCors();
  }, []);

  return (
    <Paper elevation={3} sx={{ p: 3, maxWidth: 600, mx: 'auto', mt: 4 }}>
      <Typography variant="h5" gutterBottom>
        CORS Configuration Test
      </Typography>

      <Box sx={{ my: 2 }}>
        <Typography variant="body1" gutterBottom>
          This component tests if CORS is properly configured between the frontend and backend.
        </Typography>
      </Box>

      <Box sx={{ my: 3 }}>
        <Button 
          variant="contained" 
          onClick={testCors} 
          disabled={loading}
          sx={{ mr: 2 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Test CORS'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ my: 2 }}>
          {error}
        </Alert>
      )}

      {result && (
        <Box sx={{ mt: 3, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
          <Typography variant="h6" gutterBottom>
            Success! CORS is working correctly.
          </Typography>
          <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(result, null, 2)}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default CorsTest;
