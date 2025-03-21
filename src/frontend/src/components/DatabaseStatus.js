import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Button, 
  Divider, 
  CircularProgress, 
  Alert, 
  Chip,
  Grid,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { API_BASE_URL } from '../config';

/**
 * DatabaseStatus Component
 * 
 * Displays the current database connection status and provides
 * controls for testing and reconnecting to the database.
 */
const DatabaseStatus = () => {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [statusData, setStatusData] = useState(null);
  const [testData, setTestData] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);

  // Function to fetch database status
  const fetchDatabaseStatus = async () => {
    setRefreshing(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/db-status`);
      const data = await response.json();
      
      setStatusData(data);
    } catch (err) {
      console.error('Error fetching database status:', err);
      setError('Failed to fetch database status. See console for details.');
    } finally {
      setRefreshing(false);
    }
  };

  // Function to test database connection
  const testDatabaseConnection = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/db-test`);
      const data = await response.json();
      
      setTestData(data);
    } catch (err) {
      console.error('Error testing database connection:', err);
      setError('Failed to test database connection. See console for details.');
    } finally {
      setLoading(false);
    }
  };

  // Function to force database reconnection
  const reconnectDatabase = async () => {
    setReconnecting(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/db-reconnect`, {
        method: 'POST'
      });
      const data = await response.json();
      
      // Refresh status after reconnection
      fetchDatabaseStatus();
    } catch (err) {
      console.error('Error reconnecting to database:', err);
      setError('Failed to reconnect to database. See console for details.');
    } finally {
      setReconnecting(false);
    }
  };

  // Fetch status on component mount
  useEffect(() => {
    fetchDatabaseStatus();
    
    // Set up polling every 30 seconds
    const intervalId = setInterval(fetchDatabaseStatus, 30000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  // Get status indicator color
  const getStatusColor = () => {
    if (!statusData) return 'grey';
    
    if (statusData.is_connected) return 'success';
    if (statusData.consecutive_failures > 2) return 'error';
    return 'warning';
  };
  
  // Get status icon
  const getStatusIcon = () => {
    if (!statusData) return <CircularProgress size={20} />;
    
    if (statusData.is_connected) return <CheckCircleIcon color="success" />;
    if (statusData.consecutive_failures > 2) return <ErrorIcon color="error" />;
    return <WarningIcon color="warning" />;
  };

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" component="div">
            Database Connection Status
          </Typography>
          <IconButton onClick={fetchDatabaseStatus} disabled={refreshing}>
            {refreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
          </IconButton>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {statusData ? (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              {getStatusIcon()}
              <Typography variant="body1" sx={{ ml: 1 }}>
                Status: <strong>{statusData.status}</strong>
              </Typography>
              <Chip 
                label={statusData.is_connected ? 'Connected' : 'Disconnected'} 
                color={getStatusColor()} 
                size="small" 
                sx={{ ml: 2 }}
              />
            </Box>

            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Last Check: {new Date(statusData.last_check).toLocaleTimeString()}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Consecutive Failures: {statusData.consecutive_failures}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Host: {statusData.database_url}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Railway Internal: {statusData.railway_private_networking ? 'Yes' : 'No'}
                </Typography>
              </Grid>
            </Grid>

            {statusData.last_error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                Last Error: {statusData.last_error}
              </Alert>
            )}
          </>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress />
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button 
            variant="outlined" 
            onClick={testDatabaseConnection} 
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            Test Connection
          </Button>
          <Button 
            variant="contained" 
            color="warning" 
            onClick={reconnectDatabase} 
            disabled={reconnecting}
            startIcon={reconnecting ? <CircularProgress size={20} /> : null}
          >
            Force Reconnect
          </Button>
        </Box>

        {testData && (
          <>
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              mt: 2, 
              mb: 1, 
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
              p: 1
            }} onClick={() => setExpanded(!expanded)}>
              <Typography variant="subtitle1">
                Connection Test Results
              </Typography>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </Box>
            
            <Collapse in={expanded}>
              <Box sx={{ bgcolor: 'background.paper', p: 2, borderRadius: 1 }}>
                <Alert severity={testData.status === 'success' ? 'success' : 'error'} sx={{ mb: 2 }}>
                  {testData.message}
                </Alert>
                
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="Query Time" 
                      secondary={`${testData.query_time_ms} ms`} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Tables Found" 
                      secondary={testData.tables_found} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Campaign Mappings" 
                      secondary={testData.campaign_mappings_count} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Google Ads Data" 
                      secondary={testData.has_google_ads_data ? 'Yes' : 'No'} 
                    />
                  </ListItem>
                </List>
              </Box>
            </Collapse>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default DatabaseStatus;
