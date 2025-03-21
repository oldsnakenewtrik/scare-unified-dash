import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { 
  CssBaseline, 
  AppBar, 
  Box, 
  Toolbar, 
  Typography, 
  Paper, 
  Container, 
  Grid, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  TableSortLabel,
  TablePagination,
  Button,
  CircularProgress,
  FormControlLabel,
  Switch,
  Tabs,
  Tab,
  IconButton,
  Menu,
  MenuItem,
  Link as MuiLink
} from '@mui/material';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { Link, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import SettingsIcon from '@mui/icons-material/Settings';
import MenuIcon from '@mui/icons-material/Menu';
import UnifiedDashboard from './components/UnifiedDashboard';
import CampaignMapping from './components/CampaignMapping';
import WebSocketTest from './components/WebSocketTest';
import CorsTest from './components/CorsTest';
import DatabaseStatus from './components/DatabaseStatus';
import corsProxy from './utils/corsProxy';
import { API_BASE_URL, APP_SETTINGS } from './config';

// Create a theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#25385b', // Dark blue
    },
    secondary: {
      main: '#23c785', // Green
    },
    accent: {
      main: '#baa673', // Beige/gold
    }
  },
});

// API base URL is now imported from config.js

function App() {
  // State variables
  const [currentView, setCurrentView] = useState('dashboard');
  const [anchorEl, setAnchorEl] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [campaignData, setCampaignData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [monthTabs] = useState([]);
  const [orderBy, setOrderBy] = useState('campaign');
  const [order, setOrder] = useState('asc');
  const navigate = useNavigate();

  // Function to fetch data from API
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch all campaign data using CORS proxy
      console.log('Fetching campaign metrics data...');
      // Get today's date and first day of the month a year ago as default date range
      const today = new Date();
      const oneYearAgo = new Date(today);
      oneYearAgo.setFullYear(today.getFullYear() - 1);
      oneYearAgo.setDate(1); // First day of the month
      
      const params = {
        start_date: oneYearAgo.toISOString().split('T')[0],
        end_date: today.toISOString().split('T')[0]
      };
      console.log('Using date range:', params);
      const response = await corsProxy.get('/api/campaign-metrics', params);
      
      // Transform and store the data
      console.log('Campaign data received:', response.data.length, 'records');
      setCampaignData(response.data);
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
        // Check if the item has a date property or is Google Ads data which doesn't have date
        if (item.date) {
          const itemDate = new Date(item.date);
          return itemDate >= tab.startDate && itemDate <= tab.endDate;
        }
        return true; // Include items without date property (like Google Ads data)
      });
    }
    
    // Filter by active/archived status - only if the property exists
    if (!includeArchived) {
      filtered = filtered.filter(item => 
        item.is_active === undefined || item.is_active === true
      );
    }
    
    // Group by campaign and aggregate metrics
    const campaignMap = new Map();
    
    filtered.forEach(item => {
      // Use campaign_name if it exists, fall back to original_campaign_name for Google Ads data
      const campaignName = item.campaign_name || item.original_campaign_name || 'Unknown';
      
      if (!campaignMap.has(campaignName)) {
        campaignMap.set(campaignName, {
          campaign: campaignName,
          platform: item.platform || 'Unknown',
          network: item.network || 'Unknown',
          spend: 0,
          revenue: 0,
          clicks: 0,
          impressions: 0,
          users: 0,
          smoothLeads: 0,
          totalSales: 0,
          status: item.is_active === false ? 'Archived' : 'Active',
          cpc: 0,
          conversions: 0,
          clickCount: 0 // Helper for calculating average CPC
        });
      }
      
      const campaign = campaignMap.get(campaignName);
      // Handle Google Ads data format
      if (item.cost !== undefined) {
        campaign.spend += item.cost || 0;
      } else {
        campaign.spend += item.spend || 0;
      }
      
      campaign.revenue += item.revenue || 0;
      campaign.clicks += item.clicks || 0;
      campaign.impressions += item.impressions || 0;
      campaign.users += item.users || 0;
      campaign.smoothLeads += item.smooth_leads || 0;
      campaign.totalSales += item.total_sales || 0;
      campaign.conversions += item.conversions || 0;
      
      // For calculating average CPC
      if (item.cost && item.clicks && item.clicks > 0) {
        // For Google Ads data
        campaign.cpc += item.cost / item.clicks;
        campaign.clickCount++;
      } else if (item.cpc && item.clicks) {
        // For other data sources
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
  
  // Handle menu open/close
  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleCloseSettings = () => {
    setAnchorEl(null);
  };
  
  // Navigation handler
  const handleNavigate = (view) => {
    setCurrentView(view);
    handleCloseSettings();
  };

  // Fetch data on component mount
  useEffect(() => {
    fetchData();
  }, []); // Empty dependency array means it runs once on mount
  
  return (
    <ThemeProvider theme={theme}>
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <CssBaseline />
          <AppBar position="static" sx={{ bgcolor: '#25385b' }}>
            <Toolbar>
              <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
                <img 
                  src="/SonderCare-Company-Logo-Official-SVG (1).svg" 
                  alt="SonderCare Logo" 
                  style={{ height: '45px', marginRight: '12px' }} 
                />
              </Box>
              <Button 
                color="inherit" 
                component={Link} 
                to="/"
                sx={{ color: '#fff' }}
              >
                Dashboard
              </Button>
              <IconButton 
                size="large" 
                edge="end" 
                color="inherit" 
                aria-label="settings"
                onClick={handleMenuOpen}
                sx={{ color: '#fff' }}
              >
                <SettingsIcon />
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleCloseSettings}
              >
                <MenuItem component={Link} to="/mapping" onClick={handleCloseSettings}>Campaign Name Mapping</MenuItem>
                <MenuItem component={Link} to="/db-status" onClick={handleCloseSettings}>Database Status</MenuItem>
                <MenuItem component={Link} to="/websocket-test" onClick={handleCloseSettings}>WebSocket Test</MenuItem>
                <MenuItem component={Link} to="/cors-test" onClick={handleCloseSettings}>CORS Test</MenuItem>
              </Menu>
            </Toolbar>
          </AppBar>

          <Container sx={{ mt: 4, mb: 4 }} maxWidth={false}>
            <Routes>
              <Route path="/" element={<UnifiedDashboard />} />
              <Route path="/mapping" element={<CampaignMapping />} />
              <Route path="/db-status" element={<DatabaseStatus />} />
              <Route path="/websocket-test" element={<WebSocketTest />} />
              <Route path="/cors-test" element={<CorsTest />} />
            </Routes>
          </Container>
      </LocalizationProvider>
    </ThemeProvider>
  );
}

export default App;
