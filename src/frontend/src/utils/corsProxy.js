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

const DEFAULT_TIMEOUT = 10000;

/**
 * Makes an API call through the CORS proxy
 * @param {string} endpoint - The API endpoint to call
 * @param {Object} params - Query parameters for the API call
 * @param {Object} options - Additional options for the API call
 * @returns {Promise<Object>} - Response from the API
 */
const fetchThroughProxy = async (endpoint, params = {}, options = {}) => {
  // Build the API URL
  const baseUrl = getApiBaseUrl();
  const fullUrl = `${baseUrl}${endpoint}`;
  
  // Log the API call
  console.log(`Making API call to ${fullUrl}`, params);
  
  // Set up request options
  const axiosConfig = {
    params,
    timeout: options.timeout || DEFAULT_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  };
  
  try {
    const response = await axios.get(fullUrl, axiosConfig);
    
    // Handle the case where the API returns a 404 inside a 200 response
    // This is not ideal but sometimes happens with certain backend implementations
    if (response?.data?.status === 404) {
      console.log(`API endpoint returned 404 inside 200 response: ${endpoint}`);
      
      // Log detailed information about the response to help debugging
      console.error(`Detailed error for ${endpoint}:`, {
        statusCode: response.status,
        internalStatus: response?.data?.status,
        message: response?.data?.detail || 'No detail provided',
        endpoint
      });
      
      // For critical endpoints that the UI depends on, return an empty array to prevent crashes
      const criticalEndpoints = [
        '/api/campaign-metrics',
        '/api/campaigns-hierarchical',
        '/api/campaign-mappings',
        '/api/unmapped-campaigns'
      ];
      
      if (criticalEndpoints.includes(endpoint)) {
        console.log(`Returning empty array for ${endpoint} instead of error`);
        return { 
          data: [],
          _error: {
            type: 'INTERNAL_404',
            message: `Endpoint ${endpoint} returned a 404 inside a 200 response`,
            timestamp: new Date().toISOString()
          }
        };
      }
      
      // For non-critical endpoints, throw the error so it can be handled by the caller
      throw new Error(`API endpoint ${endpoint} returned 404 status inside 200 response`);
    }
    
    // Return the response data
    return response;
  } catch (error) {
    // Log detailed error information
    console.error(`Error calling API endpoint ${endpoint}:`, error);
    
    // Create a structured error object with detailed information
    const errorInfo = {
      type: error.response ? `HTTP_${error.response.status}` : 'NETWORK_ERROR',
      message: error.message || 'Unknown error',
      endpoint,
      timestamp: new Date().toISOString(),
    };
    
    // Add response details if available
    if (error.response) {
      errorInfo.statusCode = error.response.status;
      errorInfo.statusText = error.response.statusText;
      errorInfo.data = error.response.data;
    }
    
    // Log the structured error
    console.error('Structured API error:', errorInfo);
    
    // For critical endpoints, return an empty array with error information
    const criticalEndpoints = [
      '/api/campaign-metrics',
      '/api/campaigns-hierarchical',
      '/api/campaign-mappings',
      '/api/unmapped-campaigns'
    ];
    
    if (criticalEndpoints.includes(endpoint)) {
      return { 
        data: [],
        _error: errorInfo
      };
    }
    
    // Re-throw the error for non-critical endpoints
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
  return fetchThroughProxy(endpoint, params);
};

/**
 * Make a POST request
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const postWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy(endpoint, {}, { method: 'post', data });
};

/**
 * Make a PUT request
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const putWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy(endpoint, {}, { method: 'put', data });
};

/**
 * Make a DELETE request
 * @param {string} endpoint API endpoint
 * @returns {Promise} Axios promise with the response data
 */
export const deleteWithProxy = (endpoint) => {
  return fetchThroughProxy(endpoint, {}, { method: 'delete' });
};

export default {
  get: getWithProxy,
  post: postWithProxy,
  put: putWithProxy,
  delete: deleteWithProxy
};
