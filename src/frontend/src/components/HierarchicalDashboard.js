import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Button,
  IconButton,
  Collapse
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import axios from 'axios';

// API base URL (set in .env)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

function HierarchicalDashboard() {
  // State variables
  const [campaignData, setCampaignData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const [expandedNetworks, setExpandedNetworks] = useState({});

  // Fetch data on component mount
  useEffect(() => {
    fetchCampaignData();
  }, []);

  // Function to fetch campaign data
  const fetchCampaignData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(`${API_BASE_URL}/api/campaigns-hierarchical`);
      
      // Process the data into a hierarchical structure
      const organizedData = organizeHierarchicalData(response.data);
      setCampaignData(organizedData);
    } catch (err) {
      console.error('Error fetching campaign data:', err);
      setError('Failed to fetch campaign data. This could be due to database migration issues. Try refreshing or contact support if the problem persists.');
      
      // If we failed to get hierarchical data, try to fall back to regular campaign mappings
      try {
        // This is a temporary fallback to show something while migrations are being applied
        const mappingsResponse = await axios.get(`${API_BASE_URL}/api/campaign-mappings`);
        const fallbackData = organizeFallbackData(mappingsResponse.data);
        setCampaignData(fallbackData);
        setError('Using limited functionality mode while database updates are being applied.');
      } catch (fallbackErr) {
        console.error('Fallback data fetch failed:', fallbackErr);
      }
    } finally {
      setLoading(false);
    }
  };

  // Function to organize data into a hierarchical structure
  const organizeHierarchicalData = (data) => {
    // Group by source system
    const sourceGroups = {};
    
    data.forEach(item => {
      const source = item.source_system || 'Uncategorized';
      const network = item.network || 'Uncategorized';
      
      if (!sourceGroups[source]) {
        sourceGroups[source] = {
          name: source,
          networks: {}
        };
      }
      
      if (!sourceGroups[source].networks[network]) {
        sourceGroups[source].networks[network] = {
          name: network,
          campaigns: []
        };
      }
      
      sourceGroups[source].networks[network].campaigns.push(item);
    });
    
    // Convert to array and sort campaigns by display_order
    const result = Object.values(sourceGroups).map(source => {
      source.networks = Object.values(source.networks).map(network => {
        network.campaigns.sort((a, b) => a.display_order - b.display_order);
        return network;
      });
      
      // Sort networks alphabetically
      source.networks.sort((a, b) => a.name.localeCompare(b.name));
      return source;
    });
    
    // Sort sources alphabetically
    result.sort((a, b) => a.name.localeCompare(b.name));
    
    return result;
  };

  // Function to organize fallback data when hierarchical endpoint fails
  const organizeFallbackData = (data) => {
    // Group by source system
    const sourceGroups = {};
    
    data.forEach(item => {
      const source = item.source_system || 'Uncategorized';
      const network = item.network || 'Uncategorized';
      
      if (!sourceGroups[source]) {
        sourceGroups[source] = {
          name: source,
          networks: {}
        };
      }
      
      if (!sourceGroups[source].networks[network]) {
        sourceGroups[source].networks[network] = {
          name: network,
          campaigns: []
        };
      }
      
      sourceGroups[source].networks[network].campaigns.push({
        ...item,
        display_order: 0, // Default display order
        impressions: 0,
        clicks: 0,
        conversions: 0,
        cost: 0
      });
    });
    
    // Convert to array
    const result = Object.values(sourceGroups).map(source => {
      source.networks = Object.values(source.networks);
      
      // Sort networks alphabetically
      source.networks.sort((a, b) => a.name.localeCompare(b.name));
      return source;
    });
    
    // Sort sources alphabetically
    result.sort((a, b) => a.name.localeCompare(b.name));
    
    return result;
  };

  // Handle expanding/collapsing source accordions
  const handleSourceToggle = (source) => {
    setExpandedSources(prev => ({
      ...prev,
      [source]: !prev[source]
    }));
  };

  // Handle expanding/collapsing network accordions
  const handleNetworkToggle = (source, network) => {
    const key = `${source}|${network}`;
    setExpandedNetworks(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  // Handle drag end for reordering campaigns
  const handleDragEnd = async (result) => {
    if (!result.destination) return;
    
    const { source, destination } = result;
    const [sourceSystem, networkName] = source.droppableId.split('|');
    
    // Make sure we're in the same network
    if (source.droppableId !== destination.droppableId) return;
    
    // Clone the campaign data
    const newData = [...campaignData];
    
    // Find the source in our data
    const sourceIndex = newData.findIndex(s => s.name === sourceSystem);
    if (sourceIndex === -1) return;
    
    // Find the network in our data
    const networkIndex = newData[sourceIndex].networks.findIndex(n => n.name === networkName);
    if (networkIndex === -1) return;
    
    // Get the campaigns array
    const campaigns = newData[sourceIndex].networks[networkIndex].campaigns;
    
    // Reorder the campaigns
    const [removed] = campaigns.splice(source.index, 1);
    campaigns.splice(destination.index, 0, removed);
    
    // Update display_order for all campaigns
    campaigns.forEach((campaign, index) => {
      campaign.display_order = index;
    });
    
    // Update state
    setCampaignData(newData);
    
    // Save the new order to the backend
    try {
      const updatedOrders = campaigns.map((campaign, index) => ({
        id: campaign.id,
        display_order: index
      }));
      
      await axios.post(`${API_BASE_URL}/api/campaign-order`, updatedOrders);
    } catch (err) {
      console.error('Error saving campaign order:', err);
      // Optionally show an error message
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">{error}</Typography>
        <Button variant="contained" onClick={fetchCampaignData} sx={{ mt: 2 }}>
          Retry
        </Button>
      </Box>
    );
  }

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Campaign Dashboard
        </Typography>
        
        {campaignData.length === 0 ? (
          <Typography>No campaign data available. Please map some campaigns first.</Typography>
        ) : (
          campaignData.map((source) => (
            <Accordion 
              key={source.name}
              expanded={!!expandedSources[source.name]}
              onChange={() => handleSourceToggle(source.name)}
              sx={{ mb: 2 }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">{source.name}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                {source.networks.map((network) => (
                  <Accordion 
                    key={network.name}
                    expanded={!!expandedNetworks[`${source.name}|${network.name}`]}
                    onChange={() => handleNetworkToggle(source.name, network.name)}
                    sx={{ mb: 1 }}
                  >
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1">{network.name}</Typography>
                      <Typography variant="body2" sx={{ ml: 2, color: 'text.secondary' }}>
                        ({network.campaigns.length} campaigns)
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Droppable droppableId={`${source.name}|${network.name}`}>
                        {(provided) => (
                          <TableContainer component={Paper} ref={provided.innerRef} {...provided.droppableProps}>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell width="50px"></TableCell>
                                  <TableCell>Campaign Name</TableCell>
                                  <TableCell>Original Name</TableCell>
                                  <TableCell>Category</TableCell>
                                  <TableCell>Type</TableCell>
                                  <TableCell align="right">Impressions</TableCell>
                                  <TableCell align="right">Clicks</TableCell>
                                  <TableCell align="right">Conversions</TableCell>
                                  <TableCell align="right">Cost</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {network.campaigns.map((campaign, index) => (
                                  <Draggable 
                                    key={campaign.id} 
                                    draggableId={`campaign-${campaign.id}`} 
                                    index={index}
                                  >
                                    {(provided) => (
                                      <TableRow
                                        ref={provided.innerRef}
                                        {...provided.draggableProps}
                                        sx={{
                                          '&:nth-of-type(odd)': { backgroundColor: 'rgba(0, 0, 0, 0.04)' },
                                          '&:last-child td, &:last-child th': { border: 0 }
                                        }}
                                      >
                                        <TableCell {...provided.dragHandleProps}>
                                          <DragIndicatorIcon color="action" />
                                        </TableCell>
                                        <TableCell component="th" scope="row">
                                          {campaign.pretty_campaign_name}
                                        </TableCell>
                                        <TableCell>{campaign.original_campaign_name}</TableCell>
                                        <TableCell>{campaign.campaign_category || '-'}</TableCell>
                                        <TableCell>{campaign.campaign_type || '-'}</TableCell>
                                        <TableCell align="right">{campaign.impressions?.toLocaleString() || 0}</TableCell>
                                        <TableCell align="right">{campaign.clicks?.toLocaleString() || 0}</TableCell>
                                        <TableCell align="right">{campaign.conversions?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || 0}</TableCell>
                                        <TableCell align="right">${campaign.cost?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || 0}</TableCell>
                                      </TableRow>
                                    )}
                                  </Draggable>
                                ))}
                                {provided.placeholder}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        )}
                      </Droppable>
                    </AccordionDetails>
                  </Accordion>
                ))}
              </AccordionDetails>
            </Accordion>
          ))
        )}
      </Box>
    </DragDropContext>
  );
}

export default HierarchicalDashboard;
