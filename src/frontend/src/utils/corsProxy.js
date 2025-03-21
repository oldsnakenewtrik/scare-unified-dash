/**
 * Direct API utility for the SCARE Unified Dashboard
 * This makes direct API calls to the backend
 */
import axios from 'axios';

// Determine the API base URL based on the environment
const getApiBaseUrl = () => {
  // If we're in the Railway production environment
  if (window.location.hostname.includes('railway.app')) {
    // Use the same domain but with the backend service URL
    return 'https://scare-unified-dash-production.up.railway.app';
  }
  
  // For local development or other environments, use the environment variable or default
  return process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';
};

const API_BASE_URL = getApiBaseUrl();
console.log('Using API base URL:', API_BASE_URL);

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
    console.log(`Making direct API call to ${url}`);
    const response = await axios({
      method: method,
      url: url,
      params: params,
      data: data,
      // Don't use withCredentials when using wildcard CORS
      // withCredentials: true,
      // Add headers to help with CORS
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      // Increase timeout for slow connections
      timeout: 10000
    });
    console.log('Direct API call succeeded');
    return response;
  } catch (error) {
    console.error('API call failed:', error);
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
  delete: deleteWithProxy,
};
