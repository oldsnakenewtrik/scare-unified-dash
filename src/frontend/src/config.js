// Configuration file for frontend application

// API base URL (set in .env)
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

// WebSocket URL (set in .env)
export const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:5000';

// Application settings
export const APP_SETTINGS = {
  // Polling intervals (in milliseconds)
  refreshIntervals: {
    dashboardData: 5 * 60 * 1000, // 5 minutes
    databaseStatus: 30 * 1000,    // 30 seconds
  },
  
  // Default date ranges
  defaultDateRange: {
    startDaysAgo: 30,    // Default to 30 days ago
    endDaysAgo: 0        // Today
  },
  
  // Feature flags
  features: {
    enableWebSockets: true,
    enableDatabaseMonitoring: true,
    enableAdvancedFiltering: true
  }
};
