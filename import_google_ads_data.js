// Script to import Google Ads data directly from the local JSON file
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const https = require('https');

// API URL for the admin endpoint
const API_URL = 'https://scare-unified-dash-production.up.railway.app/api/admin/import_real_google_ads_data';

// Path to the Google Ads data JSON file
const dataFilePath = path.join(__dirname, 'google_ads_data.json');

// Configure axios to ignore SSL certificate issues (only for development)
const axiosInstance = axios.create({
  httpsAgent: new https.Agent({  
    rejectUnauthorized: false
  })
});

// Function to read the data file
function readDataFile() {
  try {
    const data = fs.readFileSync(dataFilePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading the data file:', error);
    return null;
  }
}

// Function to import the data
async function importGoogleAdsData() {
  try {
    // Read the data file
    const googleAdsData = readDataFile();
    
    if (!googleAdsData) {
      console.error('Failed to read Google Ads data file');
      return;
    }
    
    console.log(`Read ${googleAdsData.length} campaign data entries`);
    
    // Log a sample of the data for verification
    console.log('Sample data (first entry):', JSON.stringify(googleAdsData[0], null, 2));
    
    // Send the data to the API endpoint
    console.log('Sending data to API...');
    
    // Create headers with CORS workarounds
    const headers = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    };
    
    // Make the API request
    const response = await axiosInstance.post(API_URL, googleAdsData, { headers });
    
    // Log the response
    console.log('Import successful!');
    console.log('Response:', response.data);
    
  } catch (error) {
    console.error('Error importing Google Ads data:');
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
      console.error('Response headers:', error.response.headers);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error message:', error.message);
    }
  }
}

// Run the import function
console.log('Starting Google Ads data import...');
importGoogleAdsData();
