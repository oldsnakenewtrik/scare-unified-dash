import React from 'react';
import { Grid, Paper, Typography, Box } from '@mui/material';

// Helper function to format numbers
const formatNumber = (num) => {
  if (num === null || num === undefined) return 'N/A';
  
  // Format as currency if needed
  if (typeof num === 'number') {
    if (num >= 1000000) {
      return `$${(num / 1000000).toFixed(2)}M`;
    } else if (num >= 1000) {
      return `$${(num / 1000).toFixed(2)}K`;
    } else {
      return `$${num.toFixed(2)}`;
    }
  }
  
  return num.toString();
};

// Helper function to calculate totals
const calculateTotals = (data) => {
  if (!data || data.length === 0) {
    return {
      clicks: 0,
      impressions: 0,
      cost: 0,
      conversions: 0,
      revenue: 0,
      visitors: 0,
      leads: 0
    };
  }
  
  return data.reduce((acc, item) => {
    return {
      clicks: acc.clicks + (item.total_clicks || 0),
      impressions: acc.impressions + (item.total_impressions || 0),
      cost: acc.cost + (item.total_cost || 0),
      conversions: acc.conversions + (item.total_conversions || 0),
      revenue: acc.revenue + (item.total_revenue || 0),
      visitors: acc.visitors + (item.website_visitors || 0),
      leads: acc.leads + (item.salesforce_leads || 0)
    };
  }, {
    clicks: 0,
    impressions: 0,
    cost: 0,
    conversions: 0,
    revenue: 0,
    visitors: 0,
    leads: 0
  });
};

// Helper function to calculate derived metrics
const calculateDerivedMetrics = (totals) => {
  const ctr = totals.impressions > 0 ? (totals.clicks / totals.impressions) * 100 : 0;
  const cpc = totals.clicks > 0 ? totals.cost / totals.clicks : 0;
  const costPerConversion = totals.conversions > 0 ? totals.cost / totals.conversions : 0;
  const conversionRate = totals.clicks > 0 ? (totals.conversions / totals.clicks) * 100 : 0;
  const roi = totals.cost > 0 ? ((totals.revenue - totals.cost) / totals.cost) * 100 : 0;
  
  return {
    ctr,
    cpc,
    costPerConversion,
    conversionRate,
    roi
  };
};

// MetricSummaryItem component
const MetricSummaryItem = ({ title, value, subtitle }) => (
  <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
    <Typography variant="body2" color="text.secondary">
      {title}
    </Typography>
    <Typography variant="h4" component="div" sx={{ my: 1 }}>
      {value}
    </Typography>
    {subtitle && (
      <Typography variant="body2" color="text.secondary">
        {subtitle}
      </Typography>
    )}
  </Paper>
);

// Main component
const MetricsSummary = ({ data }) => {
  const totals = calculateTotals(data);
  const derivedMetrics = calculateDerivedMetrics(totals);
  
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        {/* Traffic metrics */}
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="Impressions" 
            value={totals.impressions.toLocaleString()} 
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="Clicks" 
            value={totals.clicks.toLocaleString()} 
            subtitle={`CTR: ${derivedMetrics.ctr.toFixed(2)}%`}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="Visitors" 
            value={totals.visitors.toLocaleString()} 
          />
        </Grid>
        
        {/* Conversion metrics */}
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="Conversions" 
            value={totals.conversions.toLocaleString()} 
            subtitle={`Rate: ${derivedMetrics.conversionRate.toFixed(2)}%`}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="Leads" 
            value={totals.leads.toLocaleString()} 
          />
        </Grid>
        
        {/* Financial metrics */}
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="Cost" 
            value={formatNumber(totals.cost)} 
            subtitle={`CPC: ${formatNumber(derivedMetrics.cpc)}`}
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="Revenue" 
            value={formatNumber(totals.revenue)} 
          />
        </Grid>
        <Grid item xs={6} sm={4} md={2}>
          <MetricSummaryItem 
            title="ROI" 
            value={`${derivedMetrics.roi.toFixed(2)}%`} 
          />
        </Grid>
      </Grid>
    </Box>
  );
};

export default MetricsSummary;
