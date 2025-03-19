/**
 * SCARE Unified Dashboard - CORS Bypass API Helper
 * 
 * This script provides helper functions that work directly in the browser console to:
 * 1. Check the health of the API
 * 2. Get unmapped and Google Ads campaigns
 * 3. Clear Google Ads mappings
 * 4. Import real Google Ads data
 * 
 * Copy and paste this entire script into your browser console while viewing the dashboard.
 */

// Configuration
const API_BASE_URL = 'https://scare-unified-dash-production.up.railway.app';

// CORS-bypassing request function using XMLHttpRequest
function corsRequest(endpoint, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, `${API_BASE_URL}${endpoint}`, true);
    
    // Set headers
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.withCredentials = true;
    
    // Set up event handlers
    xhr.onload = function() {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          console.log(`✅ ${endpoint} succeeded:`, response);
          resolve(response);
        } catch (e) {
          console.log(`⚠️ ${endpoint} response parsing error:`, xhr.responseText);
          reject(new Error(`Invalid JSON: ${xhr.responseText}`));
        }
      } else {
        console.log(`❌ ${endpoint} failed with status ${xhr.status}:`, xhr.responseText);
        reject(new Error(`Request failed with status ${xhr.status}: ${xhr.responseText}`));
      }
    };
    
    xhr.onerror = function() {
      console.log(`❌ ${endpoint} network error`);
      reject(new Error('Network error'));
    };
    
    // Send the request
    xhr.send(data ? JSON.stringify(data) : null);
  });
}

// API Health check
async function checkHealth() {
  console.log('Checking API health...');
  try {
    const data = await corsRequest('/health');
    console.log('API health status:', data);
    return data;
  } catch (error) {
    console.error('Health check failed:', error);
    return null;
  }
}

// Get unmapped campaigns
async function getUnmappedCampaigns() {
  console.log('Getting unmapped campaigns...');
  try {
    const data = await corsRequest('/api/unmapped-campaigns');
    console.log(`Found ${data.length} unmapped campaigns`);
    return data;
  } catch (error) {
    console.error('Failed to get unmapped campaigns:', error);
    return [];
  }
}

// Get Google Ads campaigns
async function getGoogleAdsCampaigns() {
  console.log('Getting Google Ads campaigns...');
  try {
    const data = await corsRequest('/api/google-ads/campaigns');
    console.log(`Found ${data.length} Google Ads campaigns`);
    return data;
  } catch (error) {
    console.error('Failed to get Google Ads campaigns:', error);
    return [];
  }
}

// Clear Google Ads mappings
async function clearGoogleAdsMappings() {
  if (!confirm('This will clear all Google Ads campaign mappings. Continue?')) {
    console.log('Operation cancelled');
    return { cancelled: true };
  }
  
  console.log('Clearing Google Ads mappings...');
  try {
    const data = await corsRequest('/api/admin/clear_google_ads_mappings', 'POST', {});
    console.log('Mappings cleared successfully', data);
    return data;
  } catch (error) {
    console.error('Failed to clear mappings:', error);
    
    // Try alternate approach if first attempt fails
    console.log('Trying alternate CORS approach...');
    try {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE_URL}/api/admin/clear_google_ads_mappings`, false);  // Synchronous request
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify({}));
      
      if (xhr.status >= 200 && xhr.status < 300) {
        const response = JSON.parse(xhr.responseText);
        console.log('✅ Mappings cleared successfully (alt method):', response);
        return response;
      } else {
        throw new Error(`Status ${xhr.status}: ${xhr.responseText}`);
      }
    } catch (altError) {
      console.error('Alternate approach also failed:', altError);
      return { success: false, error: error.message };
    }
  }
}

// Import real Google Ads data
async function importRealGoogleAdsData(data = null) {
  if (!confirm('This will import real Google Ads data. Continue?')) {
    console.log('Operation cancelled');
    return { cancelled: true };
  }
  
  // If no data is provided, use an empty object (the backend will fetch data)
  const payload = data || {};
  
  console.log('Importing real Google Ads data...');
  try {
    const response = await corsRequest('/api/admin/import_real_google_ads_data', 'POST', payload);
    console.log('Import successful', response);
    return response;
  } catch (error) {
    console.error('Failed to import data:', error);
    
    // Try alternate approach if first attempt fails
    console.log('Trying alternate CORS approach...');
    try {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE_URL}/api/admin/import_real_google_ads_data`, false);  // Synchronous request
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(payload));
      
      if (xhr.status >= 200 && xhr.status < 300) {
        const response = JSON.parse(xhr.responseText);
        console.log('✅ Import successful (alt method):', response);
        return response;
      } else {
        throw new Error(`Status ${xhr.status}: ${xhr.responseText}`);
      }
    } catch (altError) {
      console.error('Alternate approach also failed:', altError);
      return { success: false, error: error.message };
    }
  }
}

// Run diagnostics
async function runDiagnostics() {
  console.clear();
  console.log('%c🔍 SCARE Unified Dashboard - API Diagnostics', 'font-size:20px;font-weight:bold;color:#2196f3;');
  
  try {
    // Run health check
    await checkHealth();
    
    // Get Google Ads campaigns
    const campaigns = await getGoogleAdsCampaigns();
    
    // Get unmapped campaigns
    const unmapped = await getUnmappedCampaigns();
    
    // Print summary
    console.log('\n%c📊 Summary:', 'font-size:16px;font-weight:bold;color:#4caf50;');
    console.log(`- Google Ads Campaigns: ${campaigns.length}`);
    console.log(`- Unmapped Campaigns: ${unmapped.length}`);
    
    // Print available commands
    console.log('\n%c🔧 Available Commands:', 'font-size:16px;font-weight:bold;color:#ff9800;');
    console.log('- clearGoogleAdsMappings() - Clear all Google Ads campaign mappings');
    console.log('- importRealGoogleAdsData() - Import real Google Ads data from API');
    console.log('- runDiagnostics() - Run all diagnostics again');
  } catch (error) {
    console.error('Diagnostics failed:', error);
  }
}

// Expose functions to global scope
window.checkHealth = checkHealth;
window.getUnmappedCampaigns = getUnmappedCampaigns;
window.getGoogleAdsCampaigns = getGoogleAdsCampaigns;
window.clearGoogleAdsMappings = clearGoogleAdsMappings;
window.importRealGoogleAdsData = importRealGoogleAdsData;
window.runDiagnostics = runDiagnostics;

// Run diagnostics on startup
runDiagnostics();

console.log('%c✨ API helper loaded! Copy commands from above to run them.', 'font-style:italic;color:#607d8b;');
