import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { 
  CssBaseline, 
  AppBar, 
  Toolbar, 
  Typography, 
  Container, 
  Grid, 
  Paper, 
  Box,
  CircularProgress,
  TextField,
  Button,
  Tabs,
  Tab,
  FormControlLabel,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  IconButton,
  Menu,
  MenuItem
} from '@mui/material';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { format, subDays, subMonths, parse } from 'date-fns';
import SettingsIcon from '@mui/icons-material/Settings';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';
import corsProxy from './utils/corsProxy';

// Import components
import CampaignMapping from './components/CampaignMapping';
import HierarchicalDashboard from './components/HierarchicalDashboard';
import WebSocketTest from './components/WebSocketTest';
import CorsTest from './components/CorsTest';

// Create a theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

// API base URL (set in .env)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

// Function to generate tabs for the last 12 months
const generateMonthTabs = () => {
  const tabs = [];
  const today = new Date();
  
  // Add an "All Time" tab
  tabs.push({
    label: 'All Time',
    value: 'all',
    startDate: null,
    endDate: null
  });
  
  // Add tabs for the last 12 months
  for (let i = 0; i < 12; i++) {
    const date = subMonths(today, i);
    const monthYear = format(date, 'MMM yyyy');
    const startDate = new Date(date.getFullYear(), date.getMonth(), 1);
    const endDate = new Date(date.getFullYear(), date.getMonth() + 1, 0);
    
    tabs.push({
      label: monthYear,
      value: monthYear.toLowerCase().replace(' ', '-'),
      startDate,
      endDate
    });
  }
  
  return tabs;
};

// Table columns configuration
const columns = [
  { id: 'campaign', label: 'Campaign', align: 'left', minWidth: 170 },
  { id: 'spend', label: 'Spend', align: 'right', format: (value) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) },
  { id: 'revenue', label: 'Revenue', align: 'right', format: (value) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) },
  { id: 'mer', label: 'MER', align: 'right', format: (value) => value.toFixed(2) },
  { id: 'clicks', label: 'Clicks', align: 'right', format: (value) => value.toLocaleString() },
  { id: 'users', label: 'Users', align: 'right', format: (value) => value.toLocaleString() },
  { id: 'smoothLeads', label: 'Smooth Lead', align: 'right', format: (value) => value.toLocaleString() },
  { id: 'totalSales', label: 'Total Sales', align: 'right', format: (value) => value.toLocaleString() },
  { id: 'impressions', label: 'Impressions', align: 'right', format: (value) => value.toLocaleString() },
  { id: 'cpc', label: 'Avg CPC', align: 'right', format: (value) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) },
  { id: 'status', label: 'Status', align: 'center' }
];

function App() {
  // State variables
  const [activeTab, setActiveTab] = useState('all');
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [campaignData, setCampaignData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [monthTabs] = useState(generateMonthTabs());
  const [orderBy, setOrderBy] = useState('campaign');
  const [order, setOrder] = useState('asc');
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard', 'campaign-mapping', 'cors-test', or 'websocket-test'
  
  // Settings menu state
  const [anchorEl, setAnchorEl] = useState(null);
  const openMenu = Boolean(anchorEl);
  const navigate = useNavigate();

  // Function to fetch data from API
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch all campaign data using CORS proxy
      console.log('Fetching campaign metrics data...');
      const response = await corsProxy.get('/api/campaign-metrics');
      
      // Transform and store the data
      console.log('Campaign data received:', response.data.length, 'records');
      setCampaignData(response.data);
      
      // Apply initial filtering
      filterDataByTab(activeTab, response.data, showArchived);
    } catch (err) {
      console.error('Error fetching data:', err);
      
      // Provide more detailed error information
      let errorMessage = 'Failed to fetch campaign data. ';
      
      if (err.code === 'ECONNABORTED') {
        errorMessage += 'The request timed out. The server might be under heavy load or the dataset might be too large.';
      } else if (err.response) {
        // The server responded with a status code outside the 2xx range
        errorMessage += `Server responded with status: ${err.response.status}. `;
        if (err.response.data && err.response.data.detail) {
          errorMessage += err.response.data.detail;
        }
      } else if (err.request) {
        // The request was made but no response was received
        errorMessage += 'No response received from server. Please check your network connection or try again later.';
      } else {
        // Something else happened while setting up the request
        errorMessage += err.message || 'Unknown error occurred.';
      }
      
      setError(errorMessage);
      
      console.log('Falling back to mock data due to API error');
      // For development/demo purposes, generate mock data
      const mockData = generateMockData();
      setCampaignData(mockData);
      filterDataByTab(activeTab, mockData, showArchived);
    } finally {
      setLoading(false);
    }
  };
  
  // Function to generate mock data for development/demo
  const generateMockData = () => {
    const campaignTypes = ['SEARCH', 'BRANDED', 'SOCIAL', 'DISPLAY', 'EMAIL'];
    const regions = ['US', 'CA', 'AM', 'MW'];
    const mockData = [];
    
    for (let i = 0; i < 50; i++) {
      const type = campaignTypes[Math.floor(Math.random() * campaignTypes.length)];
      const region = regions[Math.floor(Math.random() * regions.length)];
      const isActive = Math.random() > 0.3; // 70% chance of being active
      
      mockData.push({
        campaign_id: i + 1,
        campaign_name: `${type} - ${region}${i}`,
        is_active: isActive,
        spend: isActive ? Math.random() * 10000 : 0,
        revenue: isActive ? Math.random() * 20000 : 0,
        clicks: isActive ? Math.floor(Math.random() * 2000) : 0,
        impressions: isActive ? Math.floor(Math.random() * 50000) : 0,
        users: isActive ? Math.floor(Math.random() * 1500) : 0,
        smooth_leads: isActive ? Math.floor(Math.random() * 100) : 0,
        total_sales: isActive ? Math.floor(Math.random() * 50) : 0,
        cpc: isActive ? (Math.random() * 5) + 1 : 0,
        date: new Date(
          2024,
          Math.floor(Math.random() * 12),
          Math.floor(Math.random() * 28) + 1
        ).toISOString().split('T')[0]
      });
    }
    
    return mockData;
  };
  
  // Function to filter data based on active tab and archived toggle
  const filterDataByTab = (tabValue, data, includeArchived) => {
    // Find the tab configuration
    const tab = monthTabs.find(t => t.value === tabValue);
    
    if (!tab) {
      setFilteredData([]);
      return;
    }
    
    // Filter data by date range if tab has date filters
    let filtered = [...data];
    
    if (tab.startDate && tab.endDate) {
      filtered = filtered.filter(item => {
        const itemDate = new Date(item.date);
        return itemDate >= tab.startDate && itemDate <= tab.endDate;
      });
    }
    
    // Filter by active/archived status
    if (!includeArchived) {
      filtered = filtered.filter(item => item.is_active);
    }
    
    // Group by campaign and aggregate metrics
    const campaignMap = new Map();
    
    filtered.forEach(item => {
      if (!campaignMap.has(item.campaign_name)) {
        campaignMap.set(item.campaign_name, {
          campaign: item.campaign_name,
          spend: 0,
          revenue: 0,
          clicks: 0,
          impressions: 0,
          users: 0,
          smoothLeads: 0,
          totalSales: 0,
          status: item.is_active ? 'Active' : 'Archived',
          cpc: 0,
          clickCount: 0 // Helper for calculating average CPC
        });
      }
      
      const campaign = campaignMap.get(item.campaign_name);
      campaign.spend += item.spend || 0;
      campaign.revenue += item.revenue || 0;
      campaign.clicks += item.clicks || 0;
      campaign.impressions += item.impressions || 0;
      campaign.users += item.users || 0;
      campaign.smoothLeads += item.smooth_leads || 0;
      campaign.totalSales += item.total_sales || 0;
      
      // For calculating average CPC
      if (item.cpc && item.clicks) {
        campaign.cpc += item.cpc * item.clicks;
        campaign.clickCount += item.clicks;
      }
    });
    
    // Calculate derived metrics
    const aggregatedData = Array.from(campaignMap.values()).map(campaign => {
      // Calculate MER (Media Efficiency Ratio)
      campaign.mer = campaign.spend > 0 ? campaign.revenue / campaign.spend : 0;
      
      // Calculate average CPC
      campaign.cpc = campaign.clickCount > 0 ? campaign.cpc / campaign.clickCount : 0;
      
      // Remove helper properties
      delete campaign.clickCount;
      
      return campaign;
    });
    
    setFilteredData(aggregatedData);
  };
  
  // Sort function for table data
  const handleRequestSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };
  
  // Get sorted data
  const getSortedData = () => {
    return filteredData.sort((a, b) => {
      if (a[orderBy] < b[orderBy]) {
        return order === 'asc' ? -1 : 1;
      }
      if (a[orderBy] > b[orderBy]) {
        return order === 'asc' ? 1 : -1;
      }
      return 0;
    });
  };
  
  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
    filterDataByTab(newValue, campaignData, showArchived);
  };
  
  // Toggle archived campaigns
  const handleArchivedToggle = (event) => {
    setShowArchived(event.target.checked);
    filterDataByTab(activeTab, campaignData, event.target.checked);
  };
  
  // Settings menu handlers
  const handleOpenSettings = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleCloseSettings = () => {
    setAnchorEl(null);
  };
  
  const handleNavigate = (path) => {
    setCurrentView(path);
    setAnchorEl(null);
    if (path === 'dashboard') {
      navigate('/');
    } else if (path.includes('?')) {
      // Handle paths with query parameters
      navigate(`/${path}`);
    } else {
      navigate(`/${path}`);
    }
  };

  // Fetch data on component mount
  useEffect(() => {
    fetchData();
  }, []); // Empty dependency array means it runs once on mount
  
  return (
    <ThemeProvider theme={theme}>
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <CssBaseline />
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              SCARE Unified Metrics Dashboard
            </Typography>
            <Button 
              color="inherit" 
              component={Link} 
              to="/" 
              onClick={() => handleNavigate('dashboard')}
            >
              Dashboard
            </Button>
            <Button 
              color="inherit" 
              component={Link} 
              to="/hierarchy" 
              onClick={() => handleNavigate('hierarchy')}
            >
              Hierarchical View
            </Button>
            <Button 
              color="inherit" 
              component={Link} 
              to="/mapping" 
              onClick={() => handleNavigate('campaign-mapping')}
            >
              Campaign Mapping
            </Button>
            <Button 
              color="inherit" 
              component={Link} 
              to="/websocket-test" 
              onClick={() => handleNavigate('websocket-test')}
            >
              WebSocket Test
            </Button>
            <Button 
              color="inherit" 
              component={Link} 
              to="/cors-test" 
              onClick={() => handleNavigate('cors-test')}
            >
              CORS Test
            </Button>
            <IconButton
              color="inherit"
              onClick={handleOpenSettings}
              aria-label="settings"
            >
              <SettingsIcon />
            </IconButton>
            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleCloseSettings}
            >
              <MenuItem onClick={() => handleNavigate('dashboard')}>Dashboard</MenuItem>
              <MenuItem onClick={() => handleNavigate('campaign-mapping')}>Campaign Name Mapping</MenuItem>
              <MenuItem onClick={() => handleNavigate('settings/campaign-mapping?refresh=true')}>Check for New Campaigns</MenuItem>
              <MenuItem onClick={() => handleNavigate('websocket-test')}>WebSocket Test</MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          {currentView === 'dashboard' ? (
            <>
              {/* Campaign filters */}
              <Paper sx={{ p: 2, mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={showArchived}
                          onChange={handleArchivedToggle}
                          color="primary"
                        />
                      }
                      label="Show Archived Campaigns"
                    />
                  </Box>
                  <Box>
                    <Button 
                      variant="contained" 
                      onClick={fetchData}
                      disabled={loading}
                    >
                      {loading ? 'Loading...' : 'Refresh Data'}
                    </Button>
                  </Box>
                </Box>
              </Paper>
              
              {/* Error display */}
              {error && (
                <Paper sx={{ p: 2, mb: 3, bgcolor: 'error.light' }}>
                  <Typography color="error">{error}</Typography>
                </Paper>
              )}
              
              {/* Loading indicator */}
              {loading && (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                  <CircularProgress />
                </Box>
              )}
              
              {/* Month tabs */}
              <Paper sx={{ mb: 3 }}>
                <Tabs
                  value={activeTab}
                  onChange={handleTabChange}
                  indicatorColor="primary"
                  textColor="primary"
                  variant="scrollable"
                  scrollButtons="auto"
                >
                  {monthTabs.map((tab) => (
                    <Tab key={tab.value} label={tab.label} value={tab.value} />
                  ))}
                </Tabs>
              </Paper>
              
              {/* Campaign data table */}
              <Paper sx={{ width: '100%', overflow: 'hidden' }}>
                <TableContainer sx={{ maxHeight: 600 }}>
                  <Table stickyHeader aria-label="campaign metrics table">
                    <TableHead>
                      <TableRow>
                        {columns.map((column) => (
                          <TableCell
                            key={column.id}
                            align={column.align}
                            style={{ minWidth: column.minWidth }}
                            sortDirection={orderBy === column.id ? order : false}
                          >
                            <TableSortLabel
                              active={orderBy === column.id}
                              direction={orderBy === column.id ? order : 'asc'}
                              onClick={() => handleRequestSort(column.id)}
                            >
                              {column.label}
                            </TableSortLabel>
                          </TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {getSortedData().map((row, index) => {
                        return (
                          <TableRow hover role="checkbox" tabIndex={-1} key={index}>
                            {columns.map((column) => {
                              const value = row[column.id];
                              return (
                                <TableCell key={column.id} align={column.align}>
                                  {column.id === 'status' ? (
                                    <Box
                                      component="span"
                                      sx={{
                                        p: 0.5,
                                        borderRadius: 1,
                                        bgcolor: value === 'Active' ? 'success.light' : 'text.disabled',
                                        color: value === 'Active' ? 'success.dark' : 'text.primary'
                                      }}
                                    >
                                      {value}
                                    </Box>
                                  ) : column.format && value !== null ? (
                                    column.format(value)
                                  ) : (
                                    value || 'N/A'
                                  )}
                                </TableCell>
                              );
                            })}
                          </TableRow>
                        );
                      })}
                      {filteredData.length === 0 && !loading && (
                        <TableRow>
                          <TableCell colSpan={columns.length} align="center">
                            No data available for this period
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </>
          ) : currentView === 'hierarchy' ? (
            <HierarchicalDashboard />
          ) : currentView === 'campaign-mapping' ? (
            <CampaignMapping />
          ) : currentView === 'websocket-test' ? (
            <WebSocketTest />
          ) : currentView === 'cors-test' ? (
            <CorsTest />
          ) : currentView === 'settings/campaign-mapping?refresh=true' ? (
            <Button 
              variant="contained" 
              onClick={fetchData}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Refresh Data'}
            </Button>
          ) : null}
        </Container>
      </LocalizationProvider>
    </ThemeProvider>
  );
}

export default App;
