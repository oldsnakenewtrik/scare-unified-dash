// SCARE Unified Dashboard API Diagnostics
// Paste this entire script into your browser console

// Configuration
const API_BASE_URL = 'https://scare-unified-dash-production.up.railway.app';
const LOCAL_BASE_URL = 'http://localhost:8000';

// Use local URL if running locally, otherwise production
const baseUrl = window.location.hostname === 'localhost' ? LOCAL_BASE_URL : API_BASE_URL;

// Utility functions
const log = (msg, data, isError = false) => {
  const style = isError 
    ? 'background:#ff5252;color:white;padding:3px 5px;border-radius:3px;' 
    : 'background:#4caf50;color:white;padding:3px 5px;border-radius:3px;';
  
  console.log(`%c${msg}`, style, data);
};

const fetchWithTimeout = async (url, options = {}, timeout = 10000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    // For non-GET requests, handle CORS in a special way
    if (options.method && options.method !== 'GET') {
      options.mode = 'cors';
      options.credentials = 'include';
    }
    
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.headers || {}),
        'Accept': 'application/json'
      }
    });
    clearTimeout(timeoutId);
    
    // Check if response is ok (status in the range 200-299)
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error ${response.status}: ${errorText}`);
    }
    
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
};

// Load the JSON data from the active editor if possible
const getLocalGoogleAdsData = () => {
  try {
    // Try to get data from the current document
    const textArea = document.querySelector('textarea');
    if (textArea) {
      try {
        const jsonData = JSON.parse(textArea.value);
        return jsonData;
      } catch (e) {
        console.warn("Text area content is not valid JSON", e);
      }
    }
    
    // Also try to access Monaco editor if available
    if (typeof monaco !== 'undefined' && monaco.editor && monaco.editor.getModels) {
      const models = monaco.editor.getModels();
      if (models.length > 0) {
        try {
          const jsonData = JSON.parse(models[0].getValue());
          return jsonData;
        } catch (e) {
          console.warn("Editor content is not valid JSON", e);
        }
      }
    }
    
    return null;
  } catch (e) {
    console.warn("Could not access editor content", e);
    return null;
  }
};

// Diagnostic functions
const tests = {
  async healthCheck() {
    try {
      const response = await fetchWithTimeout(`${baseUrl}/health`);
      const data = await response.json();
      log('✅ Health check successful', data);
      return { success: true, data };
    } catch (error) {
      log('❌ Health check failed', error, true);
      return { success: false, error: error.toString() };
    }
  },
  
  async unmappedCampaigns() {
    try {
      const response = await fetchWithTimeout(`${baseUrl}/api/unmapped-campaigns`);
      const data = await response.json();
      log(`✅ Unmapped campaigns: ${data.length} found`, data);
      return { success: true, data };
    } catch (error) {
      log('❌ Unmapped campaigns check failed', error, true);
      return { success: false, error: error.toString() };
    }
  },
  
  async clearGoogleAdsMappingsDirect() {
    try {
      if (!confirm('This will clear all Google Ads mappings. Are you sure?')) {
        log('⚠️ Clear Google Ads mappings cancelled', null);
        return { success: false, cancelled: true };
      }
      
      // Try to access the API directly without using the browser's fetch
      const jsonpCallback = `callback_${Date.now()}`;
      const script = document.createElement('script');
      script.src = `${baseUrl}/api/admin/clear_google_ads_mappings?callback=${jsonpCallback}`;
      
      // Create a Promise to handle the JSONP callback
      const promise = new Promise((resolve, reject) => {
        window[jsonpCallback] = (data) => {
          resolve(data);
          delete window[jsonpCallback];
          document.body.removeChild(script);
        };
        
        // Handle loading errors
        script.onerror = () => {
          reject(new Error('Failed to load script'));
          delete window[jsonpCallback];
          document.body.removeChild(script);
        };
        
        // Set a timeout
        setTimeout(() => {
          if (window[jsonpCallback]) {
            reject(new Error('Request timed out'));
            delete window[jsonpCallback];
            document.body.removeChild(script);
          }
        }, 10000);
      });
      
      document.body.appendChild(script);
      const data = await promise;
      
      log('✅ Google Ads mappings cleared', data);
      return { success: true, data };
    } catch (error) {
      log('❌ Clear Google Ads mappings failed', error, true);
      return { success: false, error: error.toString() };
    }
  },
  
  async clearGoogleAdsMappings() {
    try {
      if (!confirm('This will clear all Google Ads mappings. Are you sure?')) {
        log('⚠️ Clear Google Ads mappings cancelled', null);
        return { success: false, cancelled: true };
      }
      
      // First, try regular fetch
      try {
        const response = await fetchWithTimeout(
          `${baseUrl}/api/admin/clear_google_ads_mappings`, 
          { 
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );
        
        const data = await response.json();
        log('✅ Google Ads mappings cleared', data);
        return { success: true, data };
      } catch (fetchError) {
        log('⚠️ Fetch failed, trying alternative method', fetchError);
        
        // If that fails, try with XMLHttpRequest
        const xhr = new XMLHttpRequest();
        
        const xhrPromise = new Promise((resolve, reject) => {
          xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
              if (xhr.status === 200) {
                try {
                  const result = JSON.parse(xhr.responseText);
                  resolve(result);
                } catch (e) {
                  reject(new Error(`Failed to parse response: ${xhr.responseText}`));
                }
              } else {
                reject(new Error(`XHR failed with status ${xhr.status}: ${xhr.statusText}`));
              }
            }
          };
          
          xhr.onerror = function() {
            reject(new Error('Network error'));
          };
        });
        
        xhr.open('POST', `${baseUrl}/api/admin/clear_google_ads_mappings`, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.withCredentials = true;
        xhr.send(JSON.stringify({}));
        
        const data = await xhrPromise;
        log('✅ Google Ads mappings cleared (XHR method)', data);
        return { success: true, data };
      }
    } catch (error) {
      log('❌ Clear Google Ads mappings failed', error, true);
      return { success: false, error: error.toString() };
    }
  },
  
  async importRealGoogleAdsData(jsonData = null) {
    try {
      if (!confirm('This will import real Google Ads data. Continue?')) {
        log('⚠️ Import Google Ads data cancelled', null);
        return { success: false, cancelled: true };
      }
      
      // If data is provided, use it directly
      if (jsonData) {
        log('Using provided JSON data', jsonData);
      } else {
        // Check for data in editor
        const editorData = getLocalGoogleAdsData();
        if (editorData) {
          jsonData = editorData;
          log('Using data from editor', jsonData);
        } else {
          // Prompt user to paste JSON data
          const pastedData = prompt('Paste your JSON data (or cancel to use sample data):');
          
          if (pastedData) {
            try {
              jsonData = JSON.parse(pastedData);
              log('Using pasted JSON data', jsonData);
            } catch (parseError) {
              log('❌ Invalid JSON data', parseError, true);
              if (!confirm('Invalid JSON. Continue with sample data?')) {
                return { success: false, error: 'Invalid JSON data' };
              }
            }
          } else {
            log('No data provided, using sample data');
          }
        }
      }
      
      // Now post the data to the import endpoint
      try {
        const response = await fetchWithTimeout(
          `${baseUrl}/api/admin/import_real_google_ads_data`, 
          { 
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: jsonData ? JSON.stringify(jsonData) : '{}'
          }
        );
        
        const data = await response.json();
        log('✅ Google Ads data import response', data);
        
        if (data.success) {
          log('✅ Google Ads data imported successfully', data);
          // Refresh unmapped campaigns to see the new data
          await tests.unmappedCampaigns();
          return { success: true, data };
        } else {
          log('❌ Google Ads data import failed', data.error || 'Unknown error', true);
          return { success: false, error: data.error || 'Unknown error' };
        }
      } catch (fetchError) {
        log('⚠️ Fetch failed, trying alternative method', fetchError);
        
        // If that fails, try with XMLHttpRequest
        const xhr = new XMLHttpRequest();
        
        const xhrPromise = new Promise((resolve, reject) => {
          xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
              if (xhr.status === 200) {
                try {
                  const result = JSON.parse(xhr.responseText);
                  resolve(result);
                } catch (e) {
                  reject(new Error(`Failed to parse response: ${xhr.responseText}`));
                }
              } else {
                reject(new Error(`XHR failed with status ${xhr.status}: ${xhr.statusText}`));
              }
            }
          };
          
          xhr.onerror = function() {
            reject(new Error('Network error'));
          };
        });
        
        xhr.open('POST', `${baseUrl}/api/admin/import_real_google_ads_data`, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.withCredentials = true;
        xhr.send(jsonData ? JSON.stringify(jsonData) : '{}');
        
        const data = await xhrPromise;
        log('✅ Google Ads data imported successfully (XHR method)', data);
        // Refresh unmapped campaigns to see the new data
        await tests.unmappedCampaigns();
        return { success: true, data };
      }
    } catch (error) {
      log('❌ Import Google Ads data failed', error, true);
      return { success: false, error: error.toString() };
    }
  },
  
  async checkGoogleAdsData() {
    try {
      const response = await fetchWithTimeout(`${baseUrl}/api/google-ads/campaigns`);
      const data = await response.json();
      
      if (Array.isArray(data)) {
        log(`✅ Google Ads campaigns: ${data.length} found`, data);
        return { success: true, data };
      } else {
        log('❌ Google Ads campaigns returned non-array data', data, true);
        return { success: false, error: 'Invalid response format' };
      }
    } catch (error) {
      log('❌ Google Ads campaigns check failed', error, true);
      return { success: false, error: error.toString() };
    }
  },
  
  async bypassCorsRequest(url, options = {}) {
    // This creates a hidden iframe that can make cross-origin requests
    const frameName = `cors_frame_${Date.now()}`;
    const iframe = document.createElement('iframe');
    iframe.name = frameName;
    iframe.style.display = 'none';
    document.body.appendChild(iframe);
    
    return new Promise((resolve, reject) => {
      try {
        // Create a form to submit the request
        const form = document.createElement('form');
        form.method = options.method || 'POST';
        form.action = url;
        form.target = frameName;
        
        // Add data as hidden fields if available
        if (options.body) {
          let data;
          if (typeof options.body === 'string') {
            try {
              data = JSON.parse(options.body);
            } catch (e) {
              data = { data: options.body };
            }
          } else {
            data = options.body;
          }
          
          for (const key in data) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = typeof data[key] === 'object' ? JSON.stringify(data[key]) : data[key];
            form.appendChild(input);
          }
        }
        
        // Set up message listener for response
        const messageHandler = (event) => {
          if (event.data && event.data.frameName === frameName) {
            window.removeEventListener('message', messageHandler);
            document.body.removeChild(iframe);
            resolve(event.data.response);
          }
        };
        
        window.addEventListener('message', messageHandler);
        
        // Set timeout
        setTimeout(() => {
          window.removeEventListener('message', messageHandler);
          document.body.removeChild(iframe);
          reject(new Error('Request timed out'));
        }, 10000);
        
        // Submit the form
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
      } catch (error) {
        document.body.removeChild(iframe);
        reject(error);
      }
    });
  }
};

// Main diagnostic runner
const runDiagnostics = async () => {
  console.clear();
  console.log('%cSCARE Unified Dashboard API Diagnostics', 'font-size:20px;font-weight:bold;color:#2196f3;');
  console.log(`Testing API at: ${baseUrl}`);
  
  // Run health check first
  const healthResult = await tests.healthCheck();
  
  if (healthResult.success) {
    await tests.unmappedCampaigns();
    await tests.checkGoogleAdsData();
    
    console.log('\n%cAdmin Commands', 'font-size:16px;font-weight:bold;color:#ff9800;');
    console.log('Run these commands manually using the following functions:');
    console.log('1. clearGoogleAdsMappings() - Clear all Google Ads mappings');
    console.log('2. importRealGoogleAdsData() - Import real Google Ads data');
    console.log('3. runFullDiagnostics() - Run all checks again after changes');
    console.log('\n%cAlternative methods to bypass CORS:', 'font-size:16px;font-weight:bold;color:#ff9800;');
    console.log('4. clearGoogleAdsMappingsDirect() - Try a different method to clear mappings');
  } else {
    console.log('%cAPI is not healthy. Fix the API before proceeding.', 'color:red;font-weight:bold');
  }
};

// Expose functions to global scope
window.clearGoogleAdsMappings = tests.clearGoogleAdsMappings;
window.clearGoogleAdsMappingsDirect = tests.clearGoogleAdsMappingsDirect;
window.importRealGoogleAdsData = tests.importRealGoogleAdsData;
window.runFullDiagnostics = runDiagnostics;

// Run diagnostics immediately
runDiagnostics().then(() => {
  console.log('\n%cDiagnostics completed. Use the functions above to perform admin actions.', 'font-style:italic;color:#607d8b;');
});
