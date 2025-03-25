/**
 * Direct API utility for the SCARE Unified Dashboard
 * This makes direct API calls to the backend
 */
import axios from 'axios';

// Allowed origins for credentials
const allowedOrigins = [
  "http://localhost:3000",
  "http://localhost:5000",
  "https://front-production-f6e6.up.railway.app",
  "https://scare-unified-dash-production.up.railway.app"
];

// Determine the API base URL based on the environment
const getApiBaseUrl = () => {
  // Get from environment variable first if available
  const envUrl = process.env.REACT_APP_API_BASE_URL;
  if (envUrl) {
    console.log('Using API base URL from environment variable:', envUrl);
    return envUrl;
  }
  
  // For Railway production environment
  if (window.location.hostname.includes('railway.app') || 
      window.location.hostname.includes('up.railway.app')) {
    
    // Point directly to the BACK service URL from Railway dashboard
    const backendUrl = 'https://scare-unified-dash-production.up.railway.app';
    console.log('Detected Railway environment, using BACK service URL:', backendUrl);
    return backendUrl;
  }
  
  // For local development
  console.log('Using local development API URL: http://localhost:5001');
  return 'http://localhost:5001';
};

const API_BASE_URL = getApiBaseUrl();
console.log('Final API base URL:', API_BASE_URL);

/**
 * Make a direct API request
 * @param {string} method HTTP method (GET, POST, PUT, DELETE)
 * @param {string} endpoint API endpoint (e.g., '/api/campaigns')
 * @param {Object} params URL parameters for GET requests
 * @param {Object} data Request body for POST/PUT requests
 * @returns {Promise} Axios promise with the response data
 */
export const fetchThroughProxy = async (method, endpoint, params = {}, data = null) => {
  const url = endpoint.startsWith('/') 
    ? `${API_BASE_URL}${endpoint}` 
    : `${API_BASE_URL}/${endpoint}`;
    
  try {
    console.log(`Making API call to ${url}`, { method, params });
    
    // Temporarily try without credentials to see if that resolves the CORS issue
    const response = await axios({
      method: method,
      url: url,
      params: params,
      data: data,
      // TEMPORARILY DISABLE CREDENTIALS to test if that's causing the CORS issue
      withCredentials: false,
      // Add headers to help with CORS
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      // Increase timeout for slow connections
      timeout: 60000
    });
    console.log('API call succeeded');
    
    // Log the entire raw response to debug issues
    console.log('Raw API response status:', response.status);
    console.log('Raw API response data structure:', 
      Array.isArray(response.data) 
        ? `Array with ${response.data.length} items` 
        : typeof response.data
    );
    
    // Enhanced API response handling for critical endpoints
    if (endpoint.includes('/api/')) {
      // Check specific endpoints that require special handling
      if (endpoint.includes('campaigns-performance')) {
        console.log('Processing campaigns-performance endpoint');
        // This endpoint needs data formatted for forEach() operations in UnifiedDashboard.js
        if (!Array.isArray(response.data)) {
          // Try to find the performance data array in standard locations
          if (response.data && typeof response.data === 'object') {
            const possibleArrayProps = ['performance', 'campaigns', 'data', 'results', 'records'];
            let foundArrayProp = null;
            
            // Check common property names first
            for (const prop of possibleArrayProps) {
              if (response.data[prop] && Array.isArray(response.data[prop])) {
                console.log(`Found performance data in '${prop}' property with ${response.data[prop].length} items`);
                foundArrayProp = prop;
                break;
              }
            }
            
            if (foundArrayProp) {
              response.data = response.data[foundArrayProp];
            } else {
              // Create empty array as fallback - better to show no data than crash
              console.warn('No performance data array found in response, using empty array');
              response.data = [];
            }
          } else {
            console.warn('Unexpected response format, using empty array');
            response.data = [];
          }
        }
      } else if (endpoint.includes('unmapped-campaigns')) {
        console.log('Processing unmapped-campaigns endpoint');
        // This endpoint needs an array for .filter() in CampaignMapping.js
        if (!Array.isArray(response.data)) {
          if (response.data && typeof response.data === 'object') {
            // Try to find the unmapped campaigns array
            const possibleArrayProps = ['unmapped_campaigns', 'campaigns', 'data'];
            let foundArray = false;
            
            for (const prop of possibleArrayProps) {
              if (response.data[prop] && Array.isArray(response.data[prop])) {
                console.log(`Found unmapped campaigns in '${prop}' property`);
                response.data = response.data[prop];
                foundArray = true;
                break;
              }
            }
            
            if (!foundArray) {
              console.warn('No unmapped campaigns array found, using empty array');
              response.data = [];
            }
          } else {
            console.warn('Unexpected unmapped-campaigns format, using empty array');
            response.data = [];
          }
        }
      } else if (endpoint.includes('campaigns-hierarchical')) {
        console.log('Processing campaigns-hierarchical endpoint');
        // This endpoint needs to return an array for the dashboard
        if (!Array.isArray(response.data)) {
          if (response.data && typeof response.data === 'object') {
            // Check for common array properties
            const possibleArrayProps = ['campaigns', 'hierarchical_campaigns', 'data', 'results'];
            let foundArray = false;
            
            for (const prop of possibleArrayProps) {
              if (response.data[prop] && Array.isArray(response.data[prop])) {
                console.log(`Found hierarchical campaigns in '${prop}' property`);
                response.data = response.data[prop];
                foundArray = true;
                break;
              }
            }
            
            // If we can't find an array property but there are keys, return empty array
            // DO NOT convert non-array objects to single-item arrays as this breaks filtering
            if (!foundArray) {
              console.warn('No hierarchical campaigns array found, using empty array');
              response.data = [];
            }
          } else {
            console.warn('Unexpected hierarchical campaigns format, using empty array');
            response.data = [];
          }
        }
      } else if (endpoint.includes('campaign-mappings')) {
        console.log('Processing campaign-mappings endpoint');
        // This endpoint needs an array for rendering the mapping table
        if (!Array.isArray(response.data)) {
          if (response.data && typeof response.data === 'object') {
            // Try to find the campaign mappings array
            const possibleArrayProps = ['mappings', 'campaign_mappings', 'data', 'results'];
            let foundArray = false;
            
            for (const prop of possibleArrayProps) {
              if (response.data[prop] && Array.isArray(response.data[prop])) {
                console.log(`Found campaign mappings in '${prop}' property`);
                response.data = response.data[prop];
                foundArray = true;
                break;
              }
            }
            
            if (!foundArray) {
              // Check if the response itself can be treated as an array
              const keys = Object.keys(response.data);
              if (keys.length > 0 && response.data[keys[0]] && typeof response.data[keys[0]] === 'object') {
                // Try to convert object of objects to array
                const mappingsArray = keys.map(key => ({
                  id: key,
                  ...response.data[key]
                }));
                console.log(`Converted object to array with ${mappingsArray.length} items`);
                response.data = mappingsArray;
                foundArray = true;
              }
            }
            
            if (!foundArray) {
              console.warn('No campaign mappings array found, using empty array');
              response.data = [];
            }
          } else {
            console.warn('Unexpected campaign mappings format, using empty array');
            response.data = [];
          }
        }
      }
      
      // Always log the final processed data structure
      console.log(`Final processed ${endpoint} data:`, 
        Array.isArray(response.data) 
          ? `Array with ${response.data.length} items` 
          : typeof response.data);
    }
    
    return response;
  } catch (error) {
    console.error('API call failed:', error);
    
    // Enhanced error logging for debugging
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Error response data:', error.response.data);
      console.error('Error response status:', error.response.status);
      console.error('Error response headers:', error.response.headers);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Error request:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error message:', error.message);
    }
    
    throw error;
  }
};

/**
 * Make a GET request
 * @param {string} endpoint API endpoint
 * @param {Object} params URL parameters
 * @returns {Promise} Axios promise with the response data
 */
export const getWithProxy = (endpoint, params = {}) => {
  return fetchThroughProxy('get', endpoint, params);
};

/**
 * Make a POST request
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const postWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy('post', endpoint, {}, data);
};

/**
 * Make a PUT request
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const putWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy('put', endpoint, {}, data);
};

/**
 * Make a DELETE request
 * @param {string} endpoint API endpoint
 * @returns {Promise} Axios promise with the response data
 */
export const deleteWithProxy = (endpoint) => {
  return fetchThroughProxy('delete', endpoint);
};

export default {
  get: getWithProxy,
  post: postWithProxy,
  put: putWithProxy,
  delete: deleteWithProxy
};
