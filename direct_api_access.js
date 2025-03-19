// SCARE Unified Dashboard - Direct API Access Script

// Configuration
const API_BASE_URL = 'https://scare-unified-dash-production.up.railway.app';

// Simple logging with status indicators
const log = (msg, data, isError = false) => {
  const style = isError 
    ? 'color:white;background:#f44336;padding:2px 5px;border-radius:3px;' 
    : 'color:white;background:#4caf50;padding:2px 5px;border-radius:3px;';
  console.log(`%c${msg}`, style, data);
};

// Try multiple methods to access the API endpoints
const callAdminEndpoint = async (endpoint, data = null) => {
  log(`Calling ${endpoint}...`, null);
  
  // Try these methods in order until one works
  const methods = [
    tryFetchRequest,
    tryXhrRequest,
    tryJsonpRequest
  ];
  
  let lastError = null;
  
  for (const method of methods) {
    try {
      const result = await method(endpoint, data);
      log(`✅ Success using ${method.name}`, result);
      return result;
    } catch (error) {
      lastError = error;
      log(`⚠️ ${method.name} failed: ${error.message}`, null, true);
      // Continue to the next method
    }
  }
  
  // If we get here, all methods failed
  throw new Error(`All API access methods failed: ${lastError.message}`);
};

// Method 1: Regular fetch with CORS headers
async function tryFetchRequest(endpoint, data = null) {
  const options = {
    method: data ? 'POST' : 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    mode: 'cors',
    credentials: 'include'
  };
  
  if (data) {
    options.body = JSON.stringify(data);
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error ${response.status}: ${errorText}`);
  }
  
  return await response.json();
}

// Method 2: XMLHttpRequest with CORS
async function tryXhrRequest(endpoint, data = null) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(data ? 'POST' : 'GET', `${API_BASE_URL}${endpoint}`, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Accept', 'application/json');
    
    xhr.onload = function() {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const result = JSON.parse(xhr.responseText);
          resolve(result);
        } catch (e) {
          reject(new Error(`Invalid JSON response: ${xhr.responseText}`));
        }
      } else {
        reject(new Error(`XHR error ${xhr.status}: ${xhr.statusText}`));
      }
    };
    
    xhr.onerror = function() {
      reject(new Error('Network error'));
    };
    
    xhr.send(data ? JSON.stringify(data) : null);
  });
}

// Method 3: JSONP request (for GET requests only)
async function tryJsonpRequest(endpoint, data = null) {
  if (data) {
    throw new Error('JSONP does not support POST requests with data');
  }
  
  return new Promise((resolve, reject) => {
    const callbackName = `jsonp_callback_${Date.now()}`;
    const script = document.createElement('script');
    
    // Add callback to global scope
    window[callbackName] = (result) => {
      // Clean up
      delete window[callbackName];
      document.body.removeChild(script);
      resolve(result);
    };
    
    // Setup error handling
    script.onerror = () => {
      delete window[callbackName];
      document.body.removeChild(script);
      reject(new Error('JSONP request failed'));
    };
    
    // Create URL with callback parameter
    const url = `${API_BASE_URL}${endpoint}${endpoint.includes('?') ? '&' : '?'}callback=${callbackName}`;
    script.src = url;
    
    // Set timeout
    const timeout = setTimeout(() => {
      if (window[callbackName]) {
        delete window[callbackName];
        document.body.removeChild(script);
        reject(new Error('JSONP request timed out'));
      }
    }, 10000);
    
    // Append to document to start the request
    document.body.appendChild(script);
  });
}

// Try to get data from current page
const getFileContent = () => {
  // Try various methods to get file content
  try {
    // Option 1: Try to get text from a textarea or Monaco editor
    const editorContent = (() => {
      // Try textarea first
      const textarea = document.querySelector('textarea');
      if (textarea && textarea.value) return textarea.value;
      
      // Try Monaco editor
      if (typeof monaco !== 'undefined' && monaco.editor) {
        const models = monaco.editor.getModels();
        if (models.length > 0) return models[0].getValue();
      }
      
      // Try CodeMirror
      if (typeof CodeMirror !== 'undefined' && CodeMirror.defaults) {
        const cm = document.querySelector('.CodeMirror');
        if (cm && cm.CodeMirror) return cm.CodeMirror.getValue();
      }
      
      return null;
    })();
    
    if (editorContent) {
      try {
        return JSON.parse(editorContent);
      } catch (e) {
        log('Content is not valid JSON', e, true);
      }
    }
    
    // Option 2: Look for JSON in pre tags
    const preTags = document.querySelectorAll('pre');
    for (const pre of preTags) {
      try {
        return JSON.parse(pre.textContent);
      } catch (e) {
        // Not JSON, continue to next pre tag
      }
    }
    
    // Option 3: Look for any element with JSON content
    const allElements = document.querySelectorAll('*');
    for (const el of allElements) {
      if (el.textContent && el.textContent.trim().startsWith('{') && el.textContent.trim().endsWith('}')) {
        try {
          return JSON.parse(el.textContent);
        } catch (e) {
          // Not JSON, continue
        }
      }
    }
    
    return null;
  } catch (e) {
    log('Error accessing file content', e, true);
    return null;
  }
};

// Main functions
const api = {
  // Health check
  async health() {
    const result = await callAdminEndpoint('/health');
    log('API Health', result);
    return result;
  },
  
  // Get unmapped campaigns
  async getUnmappedCampaigns() {
    const result = await callAdminEndpoint('/api/unmapped-campaigns');
    log(`Found ${result.length} unmapped campaigns`, result);
    return result;
  },
  
  // Get Google Ads campaigns
  async getGoogleAdsCampaigns() {
    const result = await callAdminEndpoint('/api/google-ads/campaigns');
    log(`Found ${result.length} Google Ads campaigns`, result);
    return result;
  },
  
  // Clear Google Ads mappings
  async clearGoogleAdsMappings() {
    if (!confirm('This will clear all Google Ads campaign mappings. Continue?')) {
      log('Operation cancelled by user', null);
      return { cancelled: true };
    }
    
    const result = await callAdminEndpoint('/api/admin/clear_google_ads_mappings', {});
    log('Clear Google Ads mappings result', result);
    return result;
  },
  
  // Import Google Ads data
  async importGoogleAdsData(data = null) {
    if (!confirm('This will import Google Ads data. Continue?')) {
      log('Operation cancelled by user', null);
      return { cancelled: true };
    }
    
    // Try to get data from current file if not provided
    if (!data) {
      data = getFileContent();
      if (data) {
        log('Using data from current file', { dataLength: JSON.stringify(data).length });
      } else {
        // Use sample data
        data = {
          sample: true,
          date: new Date().toISOString().split('T')[0]
        };
        log('No data found, using sample data', data);
      }
    }
    
    const result = await callAdminEndpoint('/api/admin/import_real_google_ads_data', data);
    log('Import Google Ads data result', result);
    
    // Refresh campaigns after import
    await api.getGoogleAdsCampaigns();
    await api.getUnmappedCampaigns();
    
    return result;
  },
  
  // Run diagnostics
  async runDiagnostics() {
    console.clear();
    console.log('%c🔍 SCARE Unified Dashboard - API Diagnostics', 'font-size:20px;font-weight:bold;color:#2196f3;');
    
    try {
      await api.health();
      await api.getGoogleAdsCampaigns();
      await api.getUnmappedCampaigns();
      
      console.log('\n%c📋 API Commands:', 'font-size:16px;font-weight:bold;color:#ff9800;');
      console.log('- api.clearGoogleAdsMappings() - Clear all Google Ads mappings');
      console.log('- api.importGoogleAdsData() - Import real Google Ads data');
      console.log('- api.runDiagnostics() - Run all checks again');
    } catch (error) {
      log('Diagnostics failed', error.message, true);
    }
  }
};

// Export API to global scope
window.api = api;

// Run diagnostics automatically
api.runDiagnostics().then(() => {
  console.log('\n%cDiagnostics completed. Use the api object to perform operations.', 'font-style:italic;color:#607d8b;');
});
