-- Sample data for development purposes
SET search_path TO scare_metrics, public;

-- Insert sample dates
INSERT INTO dim_date (date_id, full_date, day_of_week, day_name, month, month_name, quarter, year, is_weekend)
VALUES
  (1, '2023-01-01', 0, 'Sunday', 1, 'January', 1, 2023, true),
  (2, '2023-01-02', 1, 'Monday', 1, 'January', 1, 2023, false),
  (3, '2023-01-03', 2, 'Tuesday', 1, 'January', 1, 2023, false),
  (4, '2023-01-04', 3, 'Wednesday', 1, 'January', 1, 2023, false),
  (5, '2023-01-05', 4, 'Thursday', 1, 'January', 1, 2023, false),
  (6, '2023-01-06', 5, 'Friday', 1, 'January', 1, 2023, false),
  (7, '2023-01-07', 6, 'Saturday', 1, 'January', 1, 2023, true),
  (8, '2023-01-08', 0, 'Sunday', 1, 'January', 1, 2023, true),
  (9, '2023-01-09', 1, 'Monday', 1, 'January', 1, 2023, false),
  (10, '2023-01-10', 2, 'Tuesday', 1, 'January', 1, 2023, false)
ON CONFLICT DO NOTHING;

-- Insert sample campaigns
INSERT INTO dim_campaign (campaign_id, campaign_name, source_system, source_campaign_id, created_date, updated_date, is_active)
VALUES
  (1, 'Facebook Lead Gen Q1', 'RedTrack', 'RT-FB-LG-Q1', '2023-01-01', '2023-01-10', true),
  (2, 'Google Search Brand', 'Google Ads', 'GG-SRCH-BRAND', '2023-01-01', '2023-01-10', true),
  (3, 'Bing PPC Generic', 'Bing Ads', 'BG-PPC-GEN', '2023-01-01', '2023-01-10', true),
  (4, 'Email Nurture Campaign', 'Salesforce', 'SF-EMAIL-NURT', '2023-01-01', '2023-01-10', true),
  (5, 'Retargeting Campaign Q4 2022', 'RedTrack', 'RT-RETG-Q4-2022', '2022-10-01', '2022-12-31', false)
ON CONFLICT DO NOTHING;

-- Insert sample RedTrack data
INSERT INTO fact_redtrack (redtrack_id, date_id, campaign_id, impressions, clicks, cost, conversions, conversion_value, ctr, cpc, conversion_rate, cost_per_conversion, average_position, created_at, updated_at)
VALUES
  (1, 1, 1, 5000, 250, 125.75, 10, 500.00, 0.05, 0.50, 0.04, 12.58, 2.5, '2023-01-02 00:00:00', '2023-01-02 00:00:00'),
  (2, 2, 1, 4800, 240, 120.00, 8, 400.00, 0.05, 0.50, 0.033, 15.00, 2.7, '2023-01-03 00:00:00', '2023-01-03 00:00:00'),
  (3, 3, 1, 5200, 260, 130.00, 12, 600.00, 0.05, 0.50, 0.046, 10.83, 2.4, '2023-01-04 00:00:00', '2023-01-04 00:00:00'),
  (4, 4, 1, 5100, 255, 127.50, 11, 550.00, 0.05, 0.50, 0.043, 11.59, 2.6, '2023-01-05 00:00:00', '2023-01-05 00:00:00'),
  (5, 5, 1, 5300, 265, 132.50, 13, 650.00, 0.05, 0.50, 0.049, 10.19, 2.3, '2023-01-06 00:00:00', '2023-01-06 00:00:00')
ON CONFLICT DO NOTHING;

-- Insert sample Google Ads data
INSERT INTO fact_google_ads (google_ads_id, date_id, campaign_id, impressions, clicks, cost, conversions, conversion_value, ctr, cpc, conversion_rate, cost_per_conversion, average_position, created_at, updated_at)
VALUES
  (1, 1, 2, 8000, 400, 200.00, 20, 1000.00, 0.05, 0.50, 0.05, 10.00, 1.5, '2023-01-02 00:00:00', '2023-01-02 00:00:00'),
  (2, 2, 2, 7800, 390, 195.00, 18, 900.00, 0.05, 0.50, 0.046, 10.83, 1.7, '2023-01-03 00:00:00', '2023-01-03 00:00:00'),
  (3, 3, 2, 8200, 410, 205.00, 22, 1100.00, 0.05, 0.50, 0.054, 9.32, 1.4, '2023-01-04 00:00:00', '2023-01-04 00:00:00'),
  (4, 4, 2, 8100, 405, 202.50, 21, 1050.00, 0.05, 0.50, 0.052, 9.64, 1.6, '2023-01-05 00:00:00', '2023-01-05 00:00:00'),
  (5, 5, 2, 8300, 415, 207.50, 23, 1150.00, 0.05, 0.50, 0.055, 9.02, 1.3, '2023-01-06 00:00:00', '2023-01-06 00:00:00')
ON CONFLICT DO NOTHING;

-- Insert sample leads data
INSERT INTO fact_leads (lead_id, date_id, campaign_id, leads, lead_source, lead_type, lead_quality_score, is_qualified, created_at, updated_at)
VALUES
  (1, 1, 1, 15, 'Facebook', 'Form', 0.85, true, '2023-01-02 00:00:00', '2023-01-02 00:00:00'),
  (2, 2, 1, 12, 'Facebook', 'Form', 0.82, true, '2023-01-03 00:00:00', '2023-01-03 00:00:00'),
  (3, 3, 1, 18, 'Facebook', 'Form', 0.87, true, '2023-01-04 00:00:00', '2023-01-04 00:00:00'),
  (4, 4, 1, 16, 'Facebook', 'Form', 0.84, true, '2023-01-05 00:00:00', '2023-01-05 00:00:00'),
  (5, 5, 1, 20, 'Facebook', 'Form', 0.88, true, '2023-01-06 00:00:00', '2023-01-06 00:00:00'),
  
  (6, 1, 2, 25, 'Google', 'Search', 0.92, true, '2023-01-02 00:00:00', '2023-01-02 00:00:00'),
  (7, 2, 2, 22, 'Google', 'Search', 0.90, true, '2023-01-03 00:00:00', '2023-01-03 00:00:00'),
  (8, 3, 2, 28, 'Google', 'Search', 0.93, true, '2023-01-04 00:00:00', '2023-01-04 00:00:00'),
  (9, 4, 2, 26, 'Google', 'Search', 0.91, true, '2023-01-05 00:00:00', '2023-01-05 00:00:00'),
  (10, 5, 2, 30, 'Google', 'Search', 0.94, true, '2023-01-06 00:00:00', '2023-01-06 00:00:00')
ON CONFLICT DO NOTHING;

-- Insert sample sales data
INSERT INTO fact_sales (sale_id, date_id, campaign_id, sale_amount, sale_type, sale_source, customer_id, order_id, created_at, updated_at)
VALUES
  (1, 3, 1, 250.00, 'M', 'ONL', 'CUST-001', 'ORD-001', '2023-01-04 00:00:00', '2023-01-04 00:00:00'),
  (2, 4, 1, 300.00, 'M', 'ONL', 'CUST-002', 'ORD-002', '2023-01-05 00:00:00', '2023-01-05 00:00:00'),
  (3, 5, 1, 275.00, 'M', 'ONL', 'CUST-003', 'ORD-003', '2023-01-06 00:00:00', '2023-01-06 00:00:00'),
  
  (4, 3, 2, 500.00, 'T', 'ONL', 'CUST-004', 'ORD-004', '2023-01-04 00:00:00', '2023-01-04 00:00:00'),
  (5, 4, 2, 550.00, 'T', 'ONL', 'CUST-005', 'ORD-005', '2023-01-05 00:00:00', '2023-01-05 00:00:00'),
  (6, 5, 2, 525.00, 'T', 'ONL', 'CUST-006', 'ORD-006', '2023-01-06 00:00:00', '2023-01-06 00:00:00')
ON CONFLICT DO NOTHING;
