/**
 * CORS Proxy utility to bypass CORS issues with the API
 * This is a temporary solution until the backend CORS issues are resolved
 */
import axios from 'axios';

// Original API URL (the one that's having CORS issues)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

// Public CORS proxies - we'll try these in order
const CORS_PROXIES = [
  'https://corsproxy.io/?',
  'https://cors-anywhere.herokuapp.com/',
  'https://cors-proxy.htmldriven.com/?url=',
];

/**
 * Make a request through a CORS proxy to bypass CORS restrictions
 * @param {string} method HTTP method (GET, POST, PUT, DELETE)
 * @param {string} endpoint API endpoint (e.g., '/api/campaigns')
 * @param {Object} params URL parameters for GET requests
 * @param {Object} data Request body for POST/PUT requests
 * @returns {Promise} Axios promise with the response data
 */
export const fetchThroughProxy = async (method, endpoint, params = {}, data = null) => {
  // First try the direct API call (in case CORS is fixed)
  try {
    console.log(`Attempting direct API call to ${API_BASE_URL}${endpoint}`);
    const response = await axios({
      method: method,
      url: `${API_BASE_URL}${endpoint}`,
      params: params,
      data: data,
    });
    console.log('Direct API call succeeded');
    return response;
  } catch (error) {
    // If it's not a CORS error, or there's a different issue, throw the original error
    if (!error.message?.includes('Network Error') && !error.message?.includes('CORS')) {
      console.error('Direct API call failed with non-CORS error:', error);
      throw error;
    }
    
    console.warn('Direct API call failed due to CORS, trying proxies');
    
    // Try each CORS proxy in order
    for (let i = 0; i < CORS_PROXIES.length; i++) {
      const proxy = CORS_PROXIES[i];
      try {
        console.log(`Trying CORS proxy ${i + 1}: ${proxy}`);
        
        const proxyUrl = `${proxy}${encodeURIComponent(`${API_BASE_URL}${endpoint}`)}`;
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${proxyUrl}${proxyUrl.includes('?') ? '&' : '?'}${queryString}` : proxyUrl;
        
        const response = await axios({
          method: method,
          url: fullUrl,
          data: data,
        });
        
        console.log(`CORS proxy ${i + 1} succeeded`);
        return response;
      } catch (proxyError) {
        console.error(`CORS proxy ${i + 1} failed:`, proxyError);
        // Continue to the next proxy
      }
    }
    
    // If all proxies fail, try a final option: jsonp-cors-proxy
    try {
      console.log('Trying jsonp-cors-proxy as last resort');
      const response = await axios.get('https://jsonp-cors-proxy.vercel.app/api/proxy', {
        params: {
          url: `${API_BASE_URL}${endpoint}`,
          method: method,
          params: JSON.stringify(params),
          data: JSON.stringify(data)
        }
      });
      console.log('jsonp-cors-proxy succeeded');
      return { data: response.data };
    } catch (finalError) {
      console.error('All proxy attempts failed:', finalError);
      throw new Error('Failed to connect to API through any available proxy');
    }
  }
};

/**
 * Make a GET request through a CORS proxy
 * @param {string} endpoint API endpoint
 * @param {Object} params URL parameters
 * @returns {Promise} Axios promise with the response data
 */
export const getWithProxy = (endpoint, params = {}) => {
  return fetchThroughProxy('GET', endpoint, params);
};

/**
 * Make a POST request through a CORS proxy
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const postWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy('POST', endpoint, {}, data);
};

/**
 * Make a PUT request through a CORS proxy
 * @param {string} endpoint API endpoint
 * @param {Object} data Request body
 * @returns {Promise} Axios promise with the response data
 */
export const putWithProxy = (endpoint, data = {}) => {
  return fetchThroughProxy('PUT', endpoint, {}, data);
};

/**
 * Make a DELETE request through a CORS proxy
 * @param {string} endpoint API endpoint
 * @returns {Promise} Axios promise with the response data
 */
export const deleteWithProxy = (endpoint) => {
  return fetchThroughProxy('DELETE', endpoint);
};

export default {
  get: getWithProxy,
  post: postWithProxy,
  put: putWithProxy,
  delete: deleteWithProxy
};
