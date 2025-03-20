// Simple API proxy for SCARE Unified Dashboard
const API_URL = 'https://scare-unified-dash-production.up.railway.app';

// Function to create a proxy page for API requests
function createApiProxy(endpoint, method = 'GET', payload = null) {
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
  
  const dataUri = 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
  return window.open(dataUri, 'apiProxy', 'width=800,height=600');
}

// Create global API utility object
window.api = {
  health: () => createApiProxy('/health'),
  campaigns: () => createApiProxy('/api/google-ads/campaigns'),
  unmapped: () => createApiProxy('/api/unmapped-campaigns'),
  clearMappings: () => createApiProxy('/api/admin/clear_google_ads_mappings', 'POST', {}),
  importReal: () => createApiProxy('/api/admin/import_real_google_ads_data', 'POST', {})
};

// Display available functions
console.log('%c📡 API Functions:', 'font-weight:bold;color:#0277bd;');
console.log('api.health()        - Check API health');
console.log('api.campaigns()     - Get Google Ads campaigns');
console.log('api.unmapped()      - Get unmapped campaigns');
console.log('api.clearMappings() - Clear all Google Ads mappings');
console.log('api.importReal()    - Import real Google Ads data');
