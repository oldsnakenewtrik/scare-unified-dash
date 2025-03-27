import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import React, { useState, useEffect } from 'react';
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
  Collapse,
  Switch,
  FormControlLabel,
  Tabs,
  Tab
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ArchiveIcon from '@mui/icons-material/Archive';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import axios from 'axios';
import corsProxy from '../utils/corsProxy';

// API base URL (set in .env)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

function UnifiedDashboard() {
  // State variables for hierarchical view
  const [campaignData, setCampaignData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const [expandedNetworks, setExpandedNetworks] = useState({});
  
  // State variables for main dashboard features
  const [showArchived, setShowArchived] = useState(false);
  const [activeTab, setActiveTab] = useState('all-time');
  const [monthTabs, setMonthTabs] = useState([]);
  
  // Fetch data on component mount and when filters change
  useEffect(() => {
    generateMonthTabs();
    fetchCampaignData();
  }, [activeTab, showArchived]);
  
  // Generate month tabs for last 12 months
  const generateMonthTabs = () => {
    const tabs = [{ value: 'all-time', label: 'All Time' }];
    
    // Get current date
    const currentDate = new Date();
    
    // Create tabs for the previous 12 months
    for (let i = 0; i < 12; i++) {
      const date = new Date();
      date.setMonth(currentDate.getMonth() - i);
      
      const monthName = date.toLocaleString('default', { month: 'long' });
      const year = date.getFullYear();
      
      tabs.push({
        value: `${year}-${date.getMonth() + 1}`,
        label: `${monthName} ${year}`
      });
    }
    
    setMonthTabs(tabs);
  };
  
  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };
  
  // Handle archived toggle
  const handleArchivedToggle = (event) => {
    setShowArchived(event.target.checked);
  };
  
  // Function to fetch campaign data
  const fetchCampaignData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let apiParams = {};
      // Add date range parameters if not 'all-time'
      if (activeTab !== 'all-time') {
        const [year, month] = activeTab.split('-').map(Number);
        const startDate = new Date(year, month - 1, 1);
        const endDate = new Date(year, month, 0);
        apiParams = {
          start_date: startDate.toISOString().split('T')[0],
          end_date: endDate.toISOString().split('T')[0]
        };
        console.log("Fetching hierarchical data with date range:", apiParams);
      } else {
        console.log("Fetching hierarchical data for all time");
      }

      // Fetch hierarchical data with optional date parameters
      const response = await corsProxy.get('/api/campaigns-hierarchical', apiParams);

      // Log the raw response for debugging
      console.log('Raw hierarchical response:', response);
      
      // Enhanced data access pattern to handle both direct arrays and nested .data.data structures
      // If response.data is an array, use it directly. Otherwise, try response.data.data or default to empty array
      const responseData = Array.isArray(response?.data) 
        ? response.data 
        : (Array.isArray(response?.data?.data) ? response.data.data : []);
      
      console.log('Campaign data processed to array:', responseData); // Log data received from API
      
      // Process the data into a hierarchical structure and filter by archive status
      console.log(`Filtering data with showArchived = ${showArchived}`); // Log filter status
      const filteredData = responseData.filter(campaign => {
        // If showing archived, include all campaigns
        if (showArchived) return true;
        // Otherwise only include active campaigns (not archived)
        return campaign.is_active !== false;
      });
      console.log(`Data after filtering (showArchived=${showArchived}):`, filteredData); // Log data *after* filtering
      
      // NOTE: Date filtering is now handled by the backend /api/campaigns-hierarchical endpoint.
      // The responseData already contains metrics aggregated for the correct date range (or all time).
      // No need for a second API call or manual merging here.
      
      const organizedData = organizeHierarchicalData(filteredData); // Use filteredData directly
      setCampaignData(organizedData);
    } catch (err) {
      console.error('Error fetching campaign data:', err);
      setError(`Failed to fetch campaign data: ${err.message}`);
      // Set empty array as fallback
      setCampaignData([]);
    } finally {
      setLoading(false);
    }
  };
  
  // Function to handle archive/unarchive campaign
  const handleArchiveToggle = async (campaignId, currentState) => {
    try {
      const newState = !currentState;
      
      await corsProxy.post('/api/campaign-mappings/archive', {
        id: campaignId,
        is_active: newState
      });
      
      // Update local state
      const updatedData = campaignData.map(source => {
        const updatedNetworks = source.networks.map(network => {
          const updatedCampaigns = network.campaigns.map(campaign => {
            if (campaign.id === campaignId) {
              return {...campaign, is_active: newState};
            }
            return campaign;
          });
          return {...network, campaigns: updatedCampaigns};
        });
        return {...source, networks: updatedNetworks};
      });
      
      console.log("handleArchiveToggle - Before setCampaignData:", campaignData); // Log state BEFORE update
      setCampaignData(updatedData);
      console.log("handleArchiveToggle - After setCampaignData (updatedData):", updatedData); // Log the data we tried to set
    } catch (err) {
      console.error('Error toggling archive state:', err);
      setError('Failed to update campaign archive status.');
    }
  };

  // Function to organize data into a hierarchical structure
  const organizeHierarchicalData = (data) => {
    // Handle null/undefined input
    if (!data || !Array.isArray(data)) {
      console.warn('Invalid data received in organizeHierarchicalData:', data);
      return [];
    }
    
    // Return early if empty array
    if (data.length === 0) {
      return [];
    }
    
    // Group by source system
    const sourceGroups = {};
    
    data.forEach(item => {
      // Skip invalid items
      if (!item) return;
      
      // Use pretty names for grouping if available, otherwise fallback
      const source = item.pretty_source || item.source_system || 'Uncategorized';
      const network = item.pretty_network || item.network || 'Uncategorized';
      
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
        // Calculate network totals
        network.totals = network.campaigns.reduce((acc, campaign) => {
          acc.impressions += campaign.impressions || 0;
          acc.clicks += campaign.clicks || 0;
          acc.cost += campaign.cost || 0;
          acc.conversions += campaign.conversions || 0;
          return acc;
        }, { impressions: 0, clicks: 0, cost: 0, conversions: 0 });
        return network;
      });
      // Calculate source totals
      source.totals = source.networks.reduce((acc, network) => {
          acc.impressions += network.totals.impressions;
          acc.clicks += network.totals.clicks;
          acc.cost += network.totals.cost;
          acc.conversions += network.totals.conversions;
          return acc;
      }, { impressions: 0, clicks: 0, cost: 0, conversions: 0 });
      return source;
    });

    return result;
  };
  
  // Function to organize fallback data when hierarchical endpoint fails
  const organizeFallbackData = (mappings) => {
    // Handle null/undefined input
    if (!mappings || !Array.isArray(mappings)) {
      console.warn('Invalid mappings data received in organizeFallbackData:', mappings);
      return [];
    }
    
    // Return early if empty array
    if (mappings.length === 0) {
      return [];
    }
    
    // Group by source system (simplified version for fallback)
    const sourceGroups = {};
    
    mappings.forEach(item => {
      // Skip invalid items
      if (!item) return;
      
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
      
      // Add minimal data for display
      sourceGroups[source].networks[network].campaigns.push({
        id: item.id,
        external_campaign_id: item.external_campaign_id,
        original_campaign_name: item.original_campaign_name,
        pretty_campaign_name: item.pretty_campaign_name,
        display_order: item.display_order || 0,
        is_active: item.is_active !== false,
        impressions: 0,
        clicks: 0,
        conversions: 0,
        cost: 0
      });
    });
    
    // Convert to array
    return Object.values(sourceGroups).map(source => {
      source.networks = Object.values(source.networks);
      return source;
    });
  };
  
  // Handle drag end event for re-ordering campaigns
  const handleDragEnd = async (result) => {
    if (!result.destination) return;
    
    // Extract source and destination information
    const { source: dragSource, destination, draggableId } = result;
    
    // If dropped in the same position, do nothing
    if (dragSource.droppableId === destination.droppableId && dragSource.index === destination.index) {
      return;
    }
    
    // Parse the droppable ID to get source system and network
    const [sourceSystemName, networkName] = destination.droppableId.split('|');
    
    // Find the source system
    const sourceSystem = campaignData.find(s => s.name === sourceSystemName);
    if (!sourceSystem) return;
    
    // Find the network
    const network = sourceSystem.networks.find(n => n.name === networkName);
    if (!network) return;
    
    // Update the campaigns array with the new order
    const updatedCampaigns = Array.from(network.campaigns);
    
    // Get the campaign being dragged
    const [campaignSourceSystemName, campaignNetworkName] = dragSource.droppableId.split('|');
    const campaignSourceSystem = campaignData.find(s => s.name === campaignSourceSystemName);
    const campaignNetwork = campaignSourceSystem.networks.find(n => n.name === campaignNetworkName);
    const draggedCampaign = campaignNetwork.campaigns[dragSource.index];
    
    // If moving between networks, remove from source and add to destination
    if (dragSource.droppableId !== destination.droppableId) {
      // Remove from source array
      campaignNetwork.campaigns.splice(dragSource.index, 1);
      
      // Add to destination array
      updatedCampaigns.splice(destination.index, 0, draggedCampaign);
    } else {
      // Reorder within the same network
      const [removed] = updatedCampaigns.splice(dragSource.index, 1);
      updatedCampaigns.splice(destination.index, 0, removed);
    }
    
    // Update the local state with the new order
    const newCampaignData = campaignData.map(sourceSystem => {
      if (sourceSystem.name === sourceSystemName) {
        return {
          ...sourceSystem,
          networks: sourceSystem.networks.map(net => {
            if (net.name === networkName) {
              return {
                ...net,
                campaigns: updatedCampaigns
              };
            }
            return net;
          })
        };
      } else if (sourceSystem.name === campaignSourceSystemName && dragSource.droppableId !== destination.droppableId) {
        return {
          ...sourceSystem,
          networks: sourceSystem.networks.map(net => {
            if (net.name === campaignNetworkName) {
              return {
                ...net,
                campaigns: net.campaigns // Already updated above
              };
            }
            return net;
          })
        };
      }
      return sourceSystem;
    });
    
    setCampaignData(newCampaignData);
    
    // Send the new order to the server
    try {
      const orders = updatedCampaigns.map((campaign, index) => ({
        id: campaign.id,
        display_order: index
      }));
      
      await corsProxy.post('/api/campaign-order', orders);
    } catch (error) {
      console.error('Error updating campaign order:', error);
      setError('Failed to save campaign order. Please try again.');
    }
  };
  
  // Toggle expansion of a source system
  const toggleSourceExpansion = (sourceName) => {
    setExpandedSources(prev => ({
      ...prev,
      [sourceName]: !prev[sourceName]
    }));
  };
  
  // Toggle expansion of a network
  const toggleNetworkExpansion = (networkName) => {
    setExpandedNetworks(prev => ({
      ...prev,
      [networkName]: !prev[networkName]
    }));
  };
  
  // Calculate CTR (Click-Through Rate)
  const calculateCTR = (clicks, impressions) => {
    if (!impressions || impressions === 0) return 0;
    return (clicks / impressions) * 100;
  };
  
  // Calculate CPA (Cost Per Acquisition)
  const calculateCPA = (cost, conversions) => {
    if (!conversions || conversions === 0) return 0;
    return cost / conversions;
  };
  
  // Calculate CPC (Cost Per Click)
  const calculateCPC = (cost, clicks) => {
    if (!clicks || clicks === 0) return 0;
    return cost / clicks;
  };
  
  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };
  
  // Format percentage
  const formatPercentage = (value) => {
    return `${value.toFixed(2)}%`;
  };
  
  // Format large numbers
  const formatNumber = (value) => {
    return new Intl.NumberFormat('en-US').format(value);
  };
  
  return (
    <Box sx={{ width: '100%' }}>
      {/* Filters and Controls */}
      <Paper sx={{ p: 2, mb: 3, width: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <FormControlLabel
              control={
                <Switch
                  checked={showArchived}
                  onChange={handleArchivedToggle}
                  color="secondary"
                />
              }
              label="Show Archived Campaigns"
            />
          </Box>
          <Box>
            <Button 
              variant="contained" 
              onClick={fetchCampaignData}
              disabled={loading}
              sx={{ mr: 2, bgcolor: '#23c785', '&:hover': { bgcolor: '#1ea06a' } }}
            >
              {loading ? 'Loading...' : 'Refresh Data'}
            </Button>
          </Box>
        </Box>
      </Paper>
      
      {/* Month tabs */}
      <Paper sx={{ mb: 3, width: '100%' }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="secondary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
          sx={{ 
            '& .MuiTab-root': { color: '#25385b' },
            '& .Mui-selected': { color: '#23c785' }
          }}
        >
          {monthTabs.map((tab) => (
            <Tab key={tab.value} label={tab.label} value={tab.value} />
          ))}
        </Tabs>
      </Paper>
      
      {/* Error Messages */}
      {error && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'error.light', width: '100%' }}>
          <Typography color="error">{error}</Typography>
        </Paper>
      )}
      
      {/* Loading Indicator */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <DragDropContext onDragEnd={handleDragEnd}>
          {campaignData.map((sourceSystem) => (
            <Paper key={sourceSystem.name} sx={{ mb: 3, overflow: 'hidden', width: '100%' }}>
              <Accordion 
                expanded={expandedSources[sourceSystem.name] !== false}
                onChange={() => toggleSourceExpansion(sourceSystem.name)}
                sx={{ 
                  '& .MuiAccordionSummary-content': { 
                    color: '#25385b', 
                    '&.Mui-expanded': { 
                      color: '#23c785' 
                    } 
                  } 
                }}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: '#25385b' }} />}>
                  <Typography variant="h6">{sourceSystem.name}</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {Object.keys(sourceSystem.networks).length > 0 ? (
                    sourceSystem.networks.map((network) => (
                      <Accordion 
                        key={network.name}
                        expanded={expandedNetworks[network.name] !== false}
                        onChange={() => toggleNetworkExpansion(network.name)}
                        sx={{ 
                          mb: 2, 
                          width: '100%', 
                          '& .MuiAccordionSummary-content': { 
                            color: '#25385b', 
                            '&.Mui-expanded': { 
                              color: '#23c785' 
                            } 
                          } 
                        }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: '#25385b' }} />}>
                          <Typography variant="subtitle1">{network.name}</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Droppable droppableId={`droppable-${network.name}`}>
                            {(provided) => (
                              <TableContainer 
                                {...provided.droppableProps}
                                ref={provided.innerRef}
                                component={Paper} 
                                sx={{ width: '100%' }}
                              >
                                <Table>
                                  <TableHead sx={{ bgcolor: '#25385b' }}>
                                    <TableRow>
                                      <TableCell sx={{ color: 'white' }} width="5%"></TableCell>
                                      <TableCell sx={{ color: 'white' }} width="30%">Campaign</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="10%">Impressions</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="10%">Clicks</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="10%">CTR</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="10%">Cost</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="10%">CPC</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="5%">Conversions</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="5%">CPA</TableCell>
                                      <TableCell sx={{ color: 'white' }} align="right" width="5%">Actions</TableCell>
                                    </TableRow>
                                  </TableHead>
                                  <TableBody>
                                    {network.campaigns.map((campaign, index) => (
                                      <Draggable 
                                        key={`${campaign.id}-${index}`}
                                        draggableId={`${campaign.id}`}
                                        index={index}
                                      >
                                        {(provided) => (
                                          <TableRow 
                                            ref={provided.innerRef}
                                            {...provided.draggableProps}
                                            {...provided.dragHandleProps}
                                            sx={{
                                              opacity: campaign.is_active === false ? 0.6 : 1,
                                              bgcolor: campaign.is_active === false ? '#f5f5f5' : 'white',
                                              '&:hover': {
                                                backgroundColor: '#f9f9f9',
                                              },
                                            }}
                                          >
                                            <TableCell>
                                              <DragIndicatorIcon sx={{ color: '#baa673', cursor: 'move' }} />
                                            </TableCell>
                                            <TableCell>
                                              {campaign.pretty_campaign_name || campaign.original_campaign_name}
                                              <Typography variant="caption" display="block" color="textSecondary">
                                                {campaign.original_campaign_name}
                                              </Typography>
                                            </TableCell>
                                            <TableCell align="right">{formatNumber(campaign.impressions)}</TableCell>
                                            <TableCell align="right">{formatNumber(campaign.clicks)}</TableCell>
                                            <TableCell align="right">
                                              {formatPercentage(calculateCTR(campaign.clicks, campaign.impressions))}
                                            </TableCell>
                                            <TableCell align="right">{formatCurrency(campaign.cost)}</TableCell>
                                            <TableCell align="right">
                                              {formatCurrency(calculateCPC(campaign.cost, campaign.clicks))}
                                            </TableCell>
                                            <TableCell align="right">{formatNumber(campaign.conversions)}</TableCell>
                                            <TableCell align="right">
                                              {formatCurrency(calculateCPA(campaign.cost, campaign.conversions))}
                                            </TableCell>
                                            <TableCell align="center">
                                              <IconButton
                                                size="small"
                                                onClick={() => handleArchiveToggle(campaign.id, campaign.is_active)}
                                                aria-label={campaign.is_active ? "Archive campaign" : "Unarchive campaign"}
                                                sx={{ color: campaign.is_active ? '#25385b' : '#23c785' }}
                                              >
                                                {campaign.is_active ? <ArchiveIcon /> : <UnarchiveIcon />}
                                              </IconButton>
                                            </TableCell>
                                          </TableRow>
                                        )}
                                      </Draggable>
                                    ))}
                                    {provided.placeholder}
                                    {/* Network Totals Row */}
                                    <TableRow sx={{ '& td': { fontWeight: 'bold', borderTop: '2px solid #25385b' } }}>
                                      <TableCell colSpan={2} align="right">Network Total:</TableCell>
                                      <TableCell align="right">{formatNumber(network.totals.impressions)}</TableCell>
                                      <TableCell align="right">{formatNumber(network.totals.clicks)}</TableCell>
                                      <TableCell align="right">
                                        {formatPercentage(calculateCTR(network.totals.clicks, network.totals.impressions))}
                                      </TableCell>
                                      <TableCell align="right">{formatCurrency(network.totals.cost)}</TableCell>
                                      <TableCell align="right">
                                        {formatCurrency(calculateCPC(network.totals.cost, network.totals.clicks))}
                                      </TableCell>
                                      <TableCell align="right">{formatNumber(network.totals.conversions)}</TableCell>
                                      <TableCell align="right">
                                        {formatCurrency(calculateCPA(network.totals.cost, network.totals.conversions))}
                                      </TableCell>
                                      <TableCell></TableCell> {/* Empty cell for Actions column */}
                                    </TableRow>
                                  </TableBody>
                                </Table>
                              </TableContainer>
                            )}
                          </Droppable>
                        </AccordionDetails>
                      </Accordion>
                    ))
                  ) : (
                    <Typography variant="body1" sx={{ p: 2 }}>
                      No networks found for this source system.
                    </Typography>
                  )}
                  {/* Source Totals Row */}
                  {Object.keys(sourceSystem.networks).length > 0 && sourceSystem.totals && (
                    <TableContainer component={Paper} sx={{ mt: 2, borderTop: '3px solid #23c785' }}>
                      <Table size="small">
                        <TableBody>
                          <TableRow sx={{ '& td': { fontWeight: 'bold', fontSize: '1.1em' } }}>
                            <TableCell colSpan={2} align="right">{sourceSystem.name} Total:</TableCell>
                            <TableCell align="right">{formatNumber(sourceSystem.totals.impressions)}</TableCell>
                            <TableCell align="right">{formatNumber(sourceSystem.totals.clicks)}</TableCell>
                            <TableCell align="right">
                              {formatPercentage(calculateCTR(sourceSystem.totals.clicks, sourceSystem.totals.impressions))}
                            </TableCell>
                            <TableCell align="right">{formatCurrency(sourceSystem.totals.cost)}</TableCell>
                            <TableCell align="right">
                              {formatCurrency(calculateCPC(sourceSystem.totals.cost, sourceSystem.totals.clicks))}
                            </TableCell>
                            <TableCell align="right">{formatNumber(sourceSystem.totals.conversions)}</TableCell>
                            <TableCell align="right">
                              {formatCurrency(calculateCPA(sourceSystem.totals.cost, sourceSystem.totals.conversions))}
                            </TableCell>
                            <TableCell></TableCell> {/* Empty cell for Actions column */}
                          </TableRow>
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </AccordionDetails>
              </Accordion>
            </Paper>
          ))}
        </DragDropContext>
      )}
    </Box>
  );
}

export default UnifiedDashboard;
