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
 * @param {string} endpoint API endpoint (e.g., '/api/campaigns')
 * @param {string} method HTTP method (GET, POST, PUT, DELETE)
 * @param {Object} params URL parameters for GET requests
 * @param {Object} data Request body for POST/PUT requests
 * @returns {Promise} Axios promise with the response data
 */
export const fetchThroughProxy = async (endpoint, method = 'get', params = {}, data = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    console.log(`Making API call to ${url}`, {method, params});
    
    const response = await axios({
      method,
      url: url,
      params: params,
      data: data,
      withCredentials: false, // Disabled for troubleshooting CORS
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    
    // Check if the response contains an error object despite 200 status
    if (response.data && response.data.error && response.data.status_code === 404) {
      console.error(`API endpoint returned 404 inside 200 response: ${endpoint}`);
      
      // Return empty arrays for these endpoints instead of throwing errors
      if (endpoint.includes('campaign-mappings') || 
          endpoint.includes('campaign-metrics') || 
          endpoint.includes('campaigns-hierarchical') || 
          endpoint.includes('unmapped-campaigns')) {
        console.log(`Returning empty array for ${endpoint} instead of error`);
        return { data: [] };
      }
      
      // For other endpoints, throw a more helpful error
      throw new Error(`API endpoint not available: ${endpoint}`);
    }
    
    // Handle the case where response.data might not be an array for endpoints that should return arrays
    if ((endpoint.includes('campaign-mappings') || 
         endpoint.includes('campaign-metrics') || 
         endpoint.includes('campaigns-hierarchical') || 
         endpoint.includes('unmapped-campaigns')) && 
        (!response.data || !Array.isArray(response.data))) {
      console.warn(`API endpoint ${endpoint} returned non-array response:`, response.data);
      return { data: [] };
    }
    
    // Return response data in a consistent format
    return { data: Array.isArray(response.data) ? response.data : [] };
  } catch (error) {
    // Handle specific error cases with custom behavior
    if (error.response) {
      // Server responded with a status code outside of 2xx range
      console.error(`API call to ${url} failed with status ${error.response.status}:`, error.response.data);
      
      // Return empty arrays for critical endpoints instead of throwing errors
      if (endpoint.includes('campaign-mappings') || 
          endpoint.includes('campaign-metrics') || 
          endpoint.includes('campaigns-hierarchical') || 
          endpoint.includes('unmapped-campaigns')) {
        console.log(`Returning empty array for ${endpoint} after error`);
        return { data: [] };
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error(`API call to ${url} failed: No response received`, error.request);
    } else {
      // Something else happened while setting up the request
      console.error(`API call to ${url} failed: ${error.message}`);
    }
    
    // For certain endpoints, don't throw but return an empty array
    if (endpoint.includes('campaign-mappings') || 
        endpoint.includes('campaign-metrics') || 
        endpoint.includes('campaigns-hierarchical') || 
        endpoint.includes('unmapped-campaigns')) {
      console.log(`Returning empty array for ${endpoint} after error`);
      return { data: [] };
    }
    
    // For all other endpoints or errors, throw the error to be handled by caller
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
  return fetchThroughProxy(endpoint, 'get', params);
};

/**
 * Make a POST request
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const postWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy(endpoint, 'post', {}, data);
};

/**
 * Make a PUT request
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const putWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy(endpoint, 'put', {}, data);
};

/**
 * Make a DELETE request
 * @param {string} endpoint API endpoint
 * @returns {Promise} Axios promise with the response data
 */
export const deleteWithProxy = (endpoint) => {
  return fetchThroughProxy(endpoint, 'delete');
};

export default {
  get: getWithProxy,
  post: postWithProxy,
  put: putWithProxy,
  delete: deleteWithProxy
};
