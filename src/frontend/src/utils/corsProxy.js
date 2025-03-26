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
    
    // Railway deploys frontend and backend as separate services
    // The backend service might have a different URL pattern than we assumed
    // If front service is at front-production-f6e6.up.railway.app
    // Then back service is likely at back-production-[hash].up.railway.app
    
    // Try to extract environment from frontend URL
    const hostname = window.location.hostname;
    const isFrontService = hostname.startsWith('front-');
    
    let backServiceUrl;
    if (isFrontService) {
      // If frontend URL starts with 'front-', replace with 'back-'
      backServiceUrl = `https://${hostname.replace('front-', 'back-')}`;
      console.log('Detected Railway front service, using derived back service URL:', backServiceUrl);
    } else {
      // If in production but not specifically on front service,
      // try accessing API on same domain
      backServiceUrl = window.location.origin;
      console.log('Using same origin for API:', backServiceUrl);
    }
    
    return backServiceUrl;
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
      // Line 84 was a duplicate and removed
    }, // Added comma here
    // Add method and data for POST/PUT etc.
    method: options.method || 'get', // Default to 'get' if not specified
    data: options.data || undefined // Add data payload if present in options
  };
  
  try {
    // Use the generic axios(config) call instead of axios.get
    const response = await axios(axiosConfig);
    
    // Log the raw response for debugging
    console.log(`Raw response from ${endpoint} (${axiosConfig.method}):`, response);
    
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
    
    // Standardize the response data format
    // This handles various response shapes and ensures data is always accessible consistently
    const standardizedResponse = {
      ...response,
      data: standardizeResponseData(response.data, endpoint)
    };
    
    console.log(`Standardized response from ${endpoint}:`, standardizedResponse);
    
    // Return the standardized response
    return standardizedResponse;
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
 * Standardizes API response data to ensure consistent access patterns
 * This handles both direct arrays, objects, and nested data structures
 * @param {any} responseData - The raw response data from the API
 * @param {string} endpoint - The API endpoint for context logging
 * @returns {Array|Object} - The standardized response data
 */
const standardizeResponseData = (responseData, endpoint) => {
  // Log the raw data type to help with debugging
  console.log(`Response data type from ${endpoint}:`, typeof responseData, 
    Array.isArray(responseData) ? 'array' : 'not array');
  
  // Case 1: responseData is already an array - return directly
  if (Array.isArray(responseData)) {
    console.log(`${endpoint} returned direct array with ${responseData.length} items`);
    return responseData;
  }
  
  // Case 2: responseData has a data property that is an array
  if (responseData && typeof responseData === 'object' && Array.isArray(responseData.data)) {
    console.log(`${endpoint} returned nested array with ${responseData.data.length} items`);
    return responseData.data;
  }
  
  // Case 3: responseData has a data property that contains another data array (double nesting)
  if (responseData && 
      typeof responseData === 'object' && 
      responseData.data && 
      typeof responseData.data === 'object' && 
      Array.isArray(responseData.data.data)) {
    console.log(`${endpoint} returned double-nested array with ${responseData.data.data.length} items`);
    return responseData.data.data;
  }
  
  // Case 4: responseData is an object or other non-array - return as is
  // This handles the case of returning objects from API endpoints
  console.log(`${endpoint} returned non-array data:`, responseData);
  return responseData;
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
