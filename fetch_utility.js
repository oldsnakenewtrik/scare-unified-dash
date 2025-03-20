/**
 * SCARE Unified Dashboard - Fetch Utility
 * This script provides utility functions to work around CORS issues with the production API
 */

// Define base URL for API
const API_URL = 'https://scare-unified-dash-production.up.railway.app';

// Direct fetch function with no CORS
async function directFetch(endpoint, options = {}) {
  try {
    // Create iframe to bypass CORS
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    document.body.appendChild(iframe);
    
    // Create a unique callback name
    const callbackName = `callback_${Date.now()}`;
    
    // Create a promise to handle the response
    return new Promise((resolve, reject) => {
      // Set timeout to cleanup if request fails
      const timeout = setTimeout(() => {
        cleanup();
        reject(new Error('Request timed out'));
      }, 10000);
      
      // Add the callback to the window object
      window[callbackName] = (data) => {
        clearTimeout(timeout);
        cleanup();
        resolve(data);
      };
      
      // Function to clean up after request
      function cleanup() {
        document.body.removeChild(iframe);
        delete window[callbackName];
      }
      
      // Try to access via iframe
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        const script = doc.createElement('script');
        
        // Build the URL with the callback
        const url = `${API_URL}${endpoint}${endpoint.includes('?') ? '&' : '?'}callback=${callbackName}`;
        script.src = url;
        
        // Add error handler
        script.onerror = (e) => {
          clearTimeout(timeout);
          cleanup();
          reject(new Error(`Failed to load script: ${e.message}`));
        };
        
        // Add script to iframe
        doc.body.appendChild(script);
      } catch (e) {
        clearTimeout(timeout);
        cleanup();
        reject(new Error(`Failed to access iframe: ${e.message}`));
      }
    });
  } catch (error) {
    console.error('Direct fetch error:', error);
    throw error;
  }
}

// Local proxy approach - uses a data URI to create a proxy
function createProxyPage(endpoint, method = 'GET', payload = null) {
  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>API Proxy</title>
      <script>
        function sendRequest() {
          const xhr = new XMLHttpRequest();
          xhr.open('${method}', '${API_URL}${endpoint}', true);
          xhr.setRequestHeader('Content-Type', 'application/json');
          
          xhr.onload = function() {
            try {
              const data = JSON.parse(xhr.responseText);
              document.getElementById('result').textContent = JSON.stringify(data, null, 2);
              document.getElementById('status').textContent = 'Success: ' + xhr.status;
            } catch (e) {
              document.getElementById('result').textContent = xhr.responseText;
              document.getElementById('status').textContent = 'Parse Error: ' + e.message;
            }
          };
          
          xhr.onerror = function() {
            document.getElementById('status').textContent = 'Error: ' + xhr.status;
            document.getElementById('result').textContent = xhr.responseText || 'Network error';
          };
          
          ${payload ? `xhr.send(JSON.stringify(${JSON.stringify(payload)}));` : 'xhr.send();'}
        }
      </script>
    </head>
    <body onload="sendRequest()">
      <h1>API Request</h1>
      <div>Endpoint: ${endpoint}</div>
      <div>Method: ${method}</div>
      <div id="status">Loading...</div>
      <pre id="result" style="background:#f0f0f0;padding:10px;"></pre>
    </body>
    </html>
  `;
  
  // Create data URI
  const dataUri = 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
  
  // Open new window with the proxy
  const newWindow = window.open(dataUri, 'apiProxy', 'width=600,height=600');
  
  // Alert user
  alert('A new window has opened with the API request. Check that window for results.');
  
  return newWindow;
}

// Export utility functions
const utility = {
  // Get API health
  checkHealth() {
    console.log('Checking API health...');
    return createProxyPage('/health');
  },
  
  // Get Google Ads campaigns
  getGoogleAdsCampaigns() {
    console.log('Getting Google Ads campaigns...');
    return createProxyPage('/api/google-ads/campaigns');
  },
  
  // Get unmapped campaigns
  getUnmappedCampaigns() {
    console.log('Getting unmapped campaigns...');
    return createProxyPage('/api/unmapped-campaigns');
  },
  
  // Clear Google Ads mappings
  clearGoogleAdsMappings() {
    console.log('Clearing Google Ads mappings...');
    if (confirm('This will clear all Google Ads campaign mappings. Continue?')) {
      return createProxyPage('/api/admin/clear_google_ads_mappings', 'POST', {});
    } else {
      console.log('Operation cancelled');
      return null;
    }
  },
  
  // Import real Google Ads data
  importRealGoogleAdsData() {
    console.log('Importing real Google Ads data...');
    if (confirm('This will import real Google Ads data. Continue?')) {
      return createProxyPage('/api/admin/import_real_google_ads_data', 'POST', {});
    } else {
      console.log('Operation cancelled');
      return null;
    }
  }
};

// Expose utility to global scope
window.apiUtility = utility;

// Display available commands
console.log('%c🔧 API Utility Functions:', 'font-size:16px;font-weight:bold;color:#ff9800;');
console.log('- apiUtility.checkHealth() - Check API health');
console.log('- apiUtility.getGoogleAdsCampaigns() - Get all Google Ads campaigns');
console.log('- apiUtility.getUnmappedCampaigns() - Get unmapped campaigns');
console.log('- apiUtility.clearGoogleAdsMappings() - Clear all Google Ads campaign mappings');
console.log('- apiUtility.importRealGoogleAdsData() - Import real Google Ads data');
console.log('\nThese functions will open a new tab to show results and bypass CORS.');
