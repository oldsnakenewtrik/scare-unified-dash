import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Snackbar,
  Alert,
  Autocomplete,
  IconButton
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import axios from 'axios';
import corsProxy from '../utils/corsProxy';

// API base URL (set in .env)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

// Campaign data sources
const DATA_SOURCES = ['Google Ads', 'Bing Ads', 'RedTrack', 'Matomo'];

// Campaign categories and types for dropdown selections
const CAMPAIGN_CATEGORIES = ['Brand', 'Non-Brand', 'Display', 'Social', 'Affiliate', 'Email', 'Other'];
const CAMPAIGN_TYPES = ['Search', 'Display', 'Video', 'Shopping', 'App', 'Smart', 'Discovery', 'Performance Max', 'Other'];
const NETWORKS = [
  'Search', 
  'Display', 
  'Shopping', 
  'Video', 
  'Social', 
  'Affiliate', 
  'Email', 
  'Organic', 
  'Referral',
  'Direct',
  'Paid Social',
  'Native',
  'Other'
];

function CampaignMapping() {
  // Get URL parameters
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const shouldRefresh = searchParams.get('refresh') === 'true';

  // State variables
  const [activeTab, setActiveTab] = useState(0);
  const [mappedCampaigns, setMappedCampaigns] = useState([]);
  const [unmappedCampaigns, setUnmappedCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [currentMapping, setCurrentMapping] = useState({
    source_system: '',
    external_campaign_id: '',
    original_campaign_name: '',
    pretty_campaign_name: '',
    campaign_category: '',
    campaign_type: '',
    network: '',
    pretty_network: '',
    pretty_source: ''
  });

  // Helper function to get source name from tab index
  const getSourceFromTabIndex = (index) => {
    return DATA_SOURCES[index] || 'All';
  };

  // Initial data fetch
  useEffect(() => {
    fetchData();
  }, []);

  // Handle auto-refresh if URL parameter is present
  useEffect(() => {
    if (shouldRefresh) {
      handleRefreshUnmappedCampaigns();
      // Clear the URL parameter after refreshing
      window.history.replaceState({}, '', location.pathname);
    }
  }, [shouldRefresh]);

  // Load data on component mount and tab change
  useEffect(() => {
    fetchData();
  }, [activeTab]);

  // Function to fetch data from API
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Get source system from active tab
      const sourceSystem = getSourceFromTabIndex(activeTab) !== 'All' ? getSourceFromTabIndex(activeTab) : null;
      
      console.log(`Fetching campaign mappings for source: ${sourceSystem || 'All'}`);
      
      // Fetch all mapped campaigns with optional filter
      const mappedResponse = await corsProxy.get('/api/campaign-mappings', 
        sourceSystem ? { source_system: sourceSystem } : {}
      );
      
      // Check if there was an error in the response
      if (mappedResponse._error) {
        console.error('Error fetching campaign mappings:', mappedResponse._error);
        // Continue processing but log the error
      }
      
      // Log response structure for debugging
      console.log('Raw mapped campaigns response:', mappedResponse);
      
      // Ensure we have a valid response data array - Fix access pattern to handle direct array returns
      // If response.data is an array, use it directly. Otherwise, try response.data.data or default to empty array
      const mappedData = Array.isArray(mappedResponse?.data) 
        ? mappedResponse.data 
        : (mappedResponse?.data?.data || []);
      
      console.log(`Fetching unmapped campaigns...`);
      // Fetch all unmapped campaigns
      const unmappedResponse = await corsProxy.get('/api/unmapped-campaigns');
      
      // Add detailed logging to see the exact response shape
      console.log('Raw unmapped campaigns response:', unmappedResponse);
      
      // Check if there was an error in the response
      if (unmappedResponse._error) {
        console.error('Error fetching unmapped campaigns:', unmappedResponse._error);
        // Continue processing but log the error
      }
      
      // Ensure we have a valid response data array - Fix access pattern to handle direct array returns
      // If response.data is an array, use it directly. Otherwise, try response.data.data or default to empty array
      const allUnmapped = Array.isArray(unmappedResponse?.data) 
        ? unmappedResponse.data 
        : (unmappedResponse?.data?.data || []);
      
      // Filter unmapped campaigns by source if needed
      const filteredUnmapped = sourceSystem && allUnmapped.length > 0
        ? allUnmapped.filter(c => c && c.source_system === sourceSystem)
        : allUnmapped;
      
      console.log(`Received ${mappedData?.length || 0} mapped campaigns and ${filteredUnmapped?.length || 0} unmapped campaigns`);
      
      // Store the data in state
      setMappedCampaigns(mappedData);
      setUnmappedCampaigns(filteredUnmapped);
      
      // Determine if we got real data or just fallback empty arrays
      if (mappedData.length === 0 && filteredUnmapped.length === 0) {
        if (mappedResponse._error || unmappedResponse._error) {
          const errorDetail = mappedResponse._error || unmappedResponse._error;
          console.warn('API returned empty data sets due to errors:', errorDetail);
          
          // Show a more detailed error message to help diagnose backend issues
          const errorType = errorDetail.type || 'UNKNOWN';
          const errorMsg = errorDetail.message || 'Unknown error';
          
          if (errorType === 'INTERNAL_404') {
            setError('Backend API endpoints are not accessible. This may be due to database migration issues.');
          } else if (errorType.startsWith('HTTP_5')) {
            setError('Backend server error. Please check server logs for details.');
          } else {
            setError(`API Error (${errorType}): ${errorMsg}`);
          }
        } else {
          console.log('No campaigns found - this could be normal if there is no data');
          // No error to display - this could be normal if there is no data
        }
      }
    } catch (err) {
      console.error('Error in fetchData:', err);
      setError(`Failed to fetch campaign data: ${err.message}`);
      
      // Set empty arrays as fallback
      setMappedCampaigns([]);
      setUnmappedCampaigns([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch unmapped campaigns for the new tab
  const fetchUnmappedForTab = async (newTabIndex) => {
    try {
      // Fetch all unmapped campaigns
      const unmappedResponse = await corsProxy.get('/api/unmapped-campaigns');
      
      // Filter unmapped campaigns by source if needed
      const allUnmapped = unmappedResponse?.data || [];
      const filteredUnmapped = newTabIndex !== 0 
        ? allUnmapped.filter(c => c && c.source_system === DATA_SOURCES[newTabIndex - 1])
        : allUnmapped;
      
      setUnmappedCampaigns(filteredUnmapped);
    } catch (err) {
      console.error('Error fetching unmapped campaigns:', err);
      // Set fallback empty array
      setUnmappedCampaigns([]);
    }
  };

  // Handle tab change
  const handleTabChange = async (event, newValue) => {
    setActiveTab(newValue);
    await fetchUnmappedForTab(newValue);
  };

  // Open dialog for creating a new mapping
  const handleCreateMapping = (campaign) => {
    setCurrentMapping({
      source_system: campaign.source_system,
      external_campaign_id: campaign.external_campaign_id,
      original_campaign_name: campaign.original_campaign_name,
      pretty_campaign_name: campaign.original_campaign_name, // Default to original name
      campaign_category: '',
      campaign_type: '',
      network: campaign.network || '',
      pretty_network: campaign.network || '', // Default to original network
      pretty_source: campaign.source_system || '' // Default to original source
    });
    setDialogOpen(true);
  };

  // Handle input changes for creating a new mapping
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setCurrentMapping(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Helper function to handle network input - allow custom values
  const handleNetworkInputChange = (event, newValue) => {
    console.log("handleNetworkInputChange - newValue:", newValue); // DEBUG LOG
    // If it's a string (custom value) or a selected item from dropdown
    setCurrentMapping(prev => ({
      ...prev,
      network: newValue
    }));
  };

  // Helper function to handle pretty network input - allow custom values
  const handlePrettyNetworkChange = (event, newValue) => {
    console.log("handlePrettyNetworkChange - newValue:", newValue); // DEBUG LOG
    setCurrentMapping(prev => ({
      ...prev,
      pretty_network: newValue
    }));
  };

  // Helper function to handle pretty source input - allow custom values
  const handlePrettySourceChange = (event, newValue) => {
    setCurrentMapping(prev => ({
      ...prev,
      pretty_source: newValue
    }));
  };

  // Helper function to handle source system input - allow custom values
  const handleSourceSystemChange = (event, newValue) => {
    setCurrentMapping(prev => ({
      ...prev,
      source_system: newValue
    }));
  };

  // Save mapping to database
  const handleSaveMapping = async () => {
    // Log the exact object being sent
    console.log('Saving mapping data:', JSON.stringify(currentMapping, null, 2));
    try {
      await corsProxy.post('/api/campaign-mappings', currentMapping);
      setDialogOpen(false);
      setSuccess('Campaign mapping saved successfully!');
      fetchData(); // Refresh data
    } catch (err) {
      console.error('Error saving campaign mapping:', err);
      setError('Failed to save campaign mapping. Please try again.');
    }
  };

  // Delete mapping from database
  const handleDeleteMapping = async (mappingId) => {
    if (window.confirm('Are you sure you want to delete this mapping?')) {
      try {
        await corsProxy.delete(`/api/campaign-mappings/${mappingId}`);
        setSuccess('Campaign mapping deleted successfully!');
        fetchData(); // Refresh data
      } catch (err) {
        console.error('Error deleting campaign mapping:', err);
        setError('Failed to delete campaign mapping. Please try again.');
      }
    }
  };

  // Close snackbar alerts
  const handleCloseAlert = () => {
    setSuccess(null);
    setError(null);
  };

  const handleRefreshUnmappedCampaigns = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch all unmapped campaigns
      const unmappedResponse = await corsProxy.get('/api/unmapped-campaigns');
      
      // Filter unmapped campaigns by source if needed
      const allUnmapped = unmappedResponse?.data || [];
      const filteredUnmapped = activeTab !== 0 
        ? allUnmapped.filter(c => c && c.source_system === DATA_SOURCES[activeTab - 1])
        : allUnmapped;
      
      setUnmappedCampaigns(filteredUnmapped);
    } catch (err) {
      console.error('Error fetching unmapped campaigns:', err);
      // Set fallback empty array
      setUnmappedCampaigns([]);
      setError('Failed to refresh unmapped campaigns. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  // Ensure mappedCampaigns and unmappedCampaigns are always arrays
  const safeMappedCampaigns = Array.isArray(mappedCampaigns) ? mappedCampaigns : [];
  const safeUnmappedCampaigns = Array.isArray(unmappedCampaigns) ? unmappedCampaigns : [];

  return (
    <Box sx={{ width: '100%', mt: 3 }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={activeTab} 
            onChange={handleTabChange} 
            aria-label="campaign source tabs"
            variant="scrollable"
            scrollButtons="auto"
          >
            {DATA_SOURCES.map((source, index) => (
              <Tab key={index} label={source} />
            ))}
          </Tabs>
        </Box>

        <Box sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom component="div">
            Campaign Name Mapping - {getSourceFromTabIndex(activeTab)}
          </Typography>
          
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              {/* Unmapped Campaigns Section */}
              <Box sx={{ mb: 4 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    Unmapped Campaigns ({safeUnmappedCampaigns.length})
                  </Typography>
                  <IconButton 
                    color="primary" 
                    onClick={handleRefreshUnmappedCampaigns} 
                    title="Refresh unmapped campaigns"
                  >
                    <RefreshIcon />
                  </IconButton>
                </Box>
                
                {safeUnmappedCampaigns.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No unmapped campaigns found. Either all campaigns are mapped or there's no data available.
                  </Typography>
                ) : (
                  <TableContainer component={Paper} sx={{ maxHeight: 300 }}>
                    <Table stickyHeader size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Campaign Name</TableCell>
                          <TableCell>Source System</TableCell>
                          <TableCell>Network</TableCell>
                          <TableCell>External ID</TableCell>
                          <TableCell align="right">Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {safeUnmappedCampaigns.map((campaign) => (
                          <TableRow key={`${campaign.source_system || 'unknown'}-${campaign.external_campaign_id || 'unknown'}-${campaign.campaign_name || 'unknown'}`}>
                            <TableCell>{campaign.campaign_name || 'Unknown'}</TableCell>
                            <TableCell>{campaign.source_system || 'Unknown'}</TableCell>
                            <TableCell>{campaign.network || 'Unknown'}</TableCell>
                            <TableCell>{campaign.external_campaign_id}</TableCell>
                            <TableCell align="right">
                              <Button 
                                variant="contained" 
                                size="small"
                                onClick={() => handleCreateMapping({
                                  source_system: campaign.source_system,
                                  external_campaign_id: campaign.external_campaign_id,
                                  original_campaign_name: campaign.campaign_name,
                                  network: campaign.network
                                })}
                              >
                                Map
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </Box>
              
              {/* Mapped Campaigns Section */}
              <Box>
                <Typography variant="h6" gutterBottom>
                  Mapped Campaigns ({safeMappedCampaigns.length})
                </Typography>
                
                {safeMappedCampaigns.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No campaign mappings found. Map campaigns from the unmapped list above.
                  </Typography>
                ) : (
                  <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
                    <Table stickyHeader size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Original Campaign Name</TableCell>
                          <TableCell>Pretty Campaign Name</TableCell>
                          <TableCell>Category</TableCell>
                          <TableCell>Type</TableCell>
                          <TableCell>Source System</TableCell>
                          <TableCell>Pretty Source</TableCell>
                          <TableCell>Network</TableCell>
                          <TableCell>Pretty Network</TableCell>
                          <TableCell align="right">Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {safeMappedCampaigns.map((mapping) => (
                          <TableRow key={mapping?.id || `mapping-${Math.random()}`}>
                            <TableCell>{mapping?.original_campaign_name || 'Unknown'}</TableCell>
                            <TableCell>{mapping?.pretty_campaign_name || 'Unknown'}</TableCell>
                            <TableCell>{mapping?.campaign_category || 'Uncategorized'}</TableCell>
                            <TableCell>{mapping?.campaign_type || 'Uncategorized'}</TableCell>
                            <TableCell>{mapping?.source_system || 'Unknown'}</TableCell>
                            <TableCell>{mapping?.pretty_source || mapping?.source_system || 'Unknown'}</TableCell>
                            <TableCell>{mapping?.network || 'Unknown'}</TableCell>
                            <TableCell>{mapping?.pretty_network || 'Unknown'}</TableCell>
                            <TableCell align="right">
                              <Button 
                                variant="outlined" 
                                color="secondary" 
                                size="small"
                                onClick={() => handleDeleteMapping(mapping?.id)}
                              >
                                Delete
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </Box>
            </>
          )}
        </Box>
      </Paper>

      {/* Dialog for creating/editing mappings */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Map Campaign Name</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <Autocomplete
              freeSolo
              options={DATA_SOURCES}
              value={currentMapping.source_system || ''}
              onChange={handleSourceSystemChange}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Source System"
                  name="source_system"
                  variant="outlined"
                  fullWidth
                />
              )}
            />
            
            <TextField
              label="External Campaign ID"
              value={currentMapping.external_campaign_id}
              disabled
              fullWidth
            />
            
            <TextField
              label="Original Campaign Name"
              value={currentMapping.original_campaign_name}
              disabled
              fullWidth
            />
            
            <TextField
              label="Pretty Campaign Name"
              name="pretty_campaign_name"
              value={currentMapping.pretty_campaign_name}
              onChange={handleInputChange}
              required
              fullWidth
            />
            
            <FormControl fullWidth>
              <InputLabel>Campaign Category</InputLabel>
              <Select
                name="campaign_category"
                value={currentMapping.campaign_category}
                onChange={handleInputChange}
                label="Campaign Category"
              >
                {CAMPAIGN_CATEGORIES.map((category) => (
                  <MenuItem key={category} value={category}>{category}</MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl fullWidth>
              <InputLabel>Campaign Type</InputLabel>
              <Select
                name="campaign_type"
                value={currentMapping.campaign_type}
                onChange={handleInputChange}
                label="Campaign Type"
              >
                {CAMPAIGN_TYPES.map((type) => (
                  <MenuItem key={type} value={type}>{type}</MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl fullWidth>
              <InputLabel>Network</InputLabel>
              <Autocomplete
                freeSolo
                options={NETWORKS}
                value={currentMapping.network || ''}
                onChange={handleNetworkInputChange}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Network"
                    name="network"
                    variant="outlined"
                    fullWidth
                  />
                )}
              />
            </FormControl>
            
            <FormControl fullWidth>
              <InputLabel>Pretty Network</InputLabel>
              <Autocomplete
                freeSolo
                options={NETWORKS}
                value={currentMapping.pretty_network || ''}
                onChange={handlePrettyNetworkChange}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Pretty Network"
                    name="pretty_network"
                    variant="outlined"
                    fullWidth
                  />
                )}
              />
            </FormControl>
            
            <FormControl fullWidth>
              <InputLabel>Pretty Source</InputLabel>
              <Autocomplete
                freeSolo
                options={DATA_SOURCES}
                value={currentMapping.pretty_source || ''}
                onChange={handlePrettySourceChange}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Pretty Source"
                    name="pretty_source"
                    variant="outlined"
                    fullWidth
                  />
                )}
              />
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleSaveMapping} 
            variant="contained" 
            disabled={!currentMapping.pretty_campaign_name}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success and error snackbars */}
      <Snackbar open={!!success} autoHideDuration={6000} onClose={handleCloseAlert}>
        <Alert onClose={handleCloseAlert} severity="success" sx={{ width: '100%' }}>
          {success}
        </Alert>
      </Snackbar>
      
      <Snackbar open={!!error} autoHideDuration={6000} onClose={handleCloseAlert}>
        <Alert onClose={handleCloseAlert} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default CampaignMapping;
