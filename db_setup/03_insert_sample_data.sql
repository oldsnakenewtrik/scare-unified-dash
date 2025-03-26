-- PART 3: Insert sample data (run this AFTER creating all tables and views successfully)

-- Insert location data
INSERT INTO public.sm_dim_location 
(region_code, location_name, geo_target_id, country) 
VALUES
-- Canadian Provinces
('AB', 'Alberta', 1019681, 'Canada'),
('BC', 'British Columbia', 1015969, 'Canada'),
('ON', 'Ontario', 1028132, 'Canada'),
-- US States
('AZ', 'Arizona', 21136, 'United States'),
('CA', 'California', 21137, 'United States'),
('WA', 'Washington', 1014895, 'United States');

-- Insert sample campaign data
INSERT INTO public.sm_dim_campaign
(campaign_name, source_system, external_id, account_id, account_name, is_active)
VALUES
-- Google Ads Campaigns
('SCARE Solar - Search', 'Google Ads', '12345678', '123-456-7890', 'SCARE Google Ads', true),
('SCARE Solar - Display', 'Google Ads', '12345679', '123-456-7890', 'SCARE Google Ads', true),
-- Bing Ads Campaigns
('SCARE Solar - Search', 'Bing Ads', '87654321', '098-765-4321', 'SCARE Bing Ads', true),
-- RedTrack Campaigns
('SCARE Solar - Affiliate', 'RedTrack', 'RT123456', 'RT-ACC-1', 'SCARE RedTrack', true);

-- Insert campaign-location mappings
INSERT INTO public.sm_campaign_location
(campaign_id, location_id, is_primary)
VALUES
-- Link Google Ads Search campaign to locations
(1, 1, true),  -- SCARE Solar - Search (Google) to Alberta (primary)
(1, 6, false), -- SCARE Solar - Search (Google) to Washington

-- Link Google Ads Display campaign to locations
(2, 2, true),  -- SCARE Solar - Display (Google) to British Columbia (primary)
(2, 5, false), -- SCARE Solar - Display (Google) to California

-- Link Bing Ads Search campaign to locations
(3, 3, true),  -- SCARE Solar - Search (Bing) to Ontario (primary)
(3, 4, false), -- SCARE Solar - Search (Bing) to Arizona

-- Link RedTrack Affiliate campaign to locations
(4, 4, true),  -- SCARE Solar - Affiliate (RedTrack) to Arizona (primary)
(4, 6, false); -- SCARE Solar - Affiliate (RedTrack) to Washington

-- Insert sample Google Ads data for the last 7 days
INSERT INTO public.sm_fact_google_ads
(date, campaign_id, campaign_name, account_id, account_name, location_id, impressions, clicks, cost, conversions, conversion_rate, cost_per_conversion)
VALUES
-- Search Campaign - Alberta (Last 7 days)
(CURRENT_DATE - INTERVAL '0 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 1, 8754, 423, 1245.67, 18, 4.26, 69.20),
(CURRENT_DATE - INTERVAL '1 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 1, 9125, 456, 1342.88, 21, 4.61, 63.95),
(CURRENT_DATE - INTERVAL '2 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 1, 8632, 401, 1198.56, 16, 3.99, 74.91),
(CURRENT_DATE - INTERVAL '3 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 1, 7945, 387, 1156.32, 14, 3.62, 82.59),
(CURRENT_DATE - INTERVAL '4 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 1, 8123, 412, 1234.56, 17, 4.13, 72.62),
(CURRENT_DATE - INTERVAL '5 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 1, 7654, 378, 1134.23, 15, 3.97, 75.62),
(CURRENT_DATE - INTERVAL '6 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 1, 8234, 405, 1213.45, 19, 4.69, 63.87),

-- Search Campaign - Washington (Last 7 days)
(CURRENT_DATE - INTERVAL '0 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 6, 7123, 342, 1034.56, 14, 4.09, 73.90),
(CURRENT_DATE - INTERVAL '1 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 6, 7543, 368, 1123.45, 16, 4.35, 70.22),
(CURRENT_DATE - INTERVAL '2 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 6, 7234, 351, 1067.89, 13, 3.70, 82.15),
(CURRENT_DATE - INTERVAL '3 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 6, 6987, 332, 1012.34, 12, 3.61, 84.36),
(CURRENT_DATE - INTERVAL '4 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 6, 7345, 356, 1089.67, 15, 4.21, 72.64),
(CURRENT_DATE - INTERVAL '5 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 6, 6876, 321, 987.65, 11, 3.43, 89.79),
(CURRENT_DATE - INTERVAL '6 day', 1, 'SCARE Solar - Search', '123-456-7890', 'SCARE Google Ads', 6, 7234, 346, 1056.78, 14, 4.05, 75.48),

-- Display Campaign - British Columbia (Last 7 days)
(CURRENT_DATE - INTERVAL '0 day', 2, 'SCARE Solar - Display', '123-456-7890', 'SCARE Google Ads', 2, 25432, 324, 534.67, 8, 2.47, 66.83),
(CURRENT_DATE - INTERVAL '1 day', 2, 'SCARE Solar - Display', '123-456-7890', 'SCARE Google Ads', 2, 26789, 345, 567.89, 9, 2.61, 63.10),
(CURRENT_DATE - INTERVAL '2 day', 2, 'SCARE Solar - Display', '123-456-7890', 'SCARE Google Ads', 2, 24567, 318, 523.45, 7, 2.20, 74.78),
(CURRENT_DATE - INTERVAL '3 day', 2, 'SCARE Solar - Display', '123-456-7890', 'SCARE Google Ads', 2, 23987, 301, 503.21, 6, 1.99, 83.87),
(CURRENT_DATE - INTERVAL '4 day', 2, 'SCARE Solar - Display', '123-456-7890', 'SCARE Google Ads', 2, 25123, 322, 532.12, 8, 2.48, 66.52),
(CURRENT_DATE - INTERVAL '5 day', 2, 'SCARE Solar - Display', '123-456-7890', 'SCARE Google Ads', 2, 24321, 312, 512.34, 7, 2.24, 73.19),
(CURRENT_DATE - INTERVAL '6 day', 2, 'SCARE Solar - Display', '123-456-7890', 'SCARE Google Ads', 2, 25634, 328, 543.21, 9, 2.74, 60.36);

-- Insert sample Bing Ads data for the last 7 days
INSERT INTO public.sm_fact_bing_ads
(date, campaign_id, campaign_name, account_id, account_name, location_id, impressions, clicks, cost, conversions, conversion_rate, cost_per_conversion)
VALUES
-- Search Campaign - Ontario (Last 7 days)
(CURRENT_DATE - INTERVAL '0 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 3, 4532, 198, 523.45, 7, 3.54, 74.78),
(CURRENT_DATE - INTERVAL '1 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 3, 4678, 210, 545.67, 8, 3.81, 68.21),
(CURRENT_DATE - INTERVAL '2 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 3, 4321, 189, 498.76, 6, 3.17, 83.13),
(CURRENT_DATE - INTERVAL '3 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 3, 4123, 182, 478.90, 5, 2.75, 95.78),
(CURRENT_DATE - INTERVAL '4 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 3, 4432, 195, 515.43, 7, 3.59, 73.63),
(CURRENT_DATE - INTERVAL '5 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 3, 4234, 187, 492.34, 6, 3.21, 82.06),
(CURRENT_DATE - INTERVAL '6 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 3, 4567, 203, 532.87, 8, 3.94, 66.61),

-- Search Campaign - Arizona (Last 7 days)
(CURRENT_DATE - INTERVAL '0 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 4, 3876, 165, 432.12, 5, 3.03, 86.42),
(CURRENT_DATE - INTERVAL '1 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 4, 3987, 172, 450.34, 6, 3.49, 75.06),
(CURRENT_DATE - INTERVAL '2 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 4, 3765, 159, 415.67, 4, 2.52, 103.92),
(CURRENT_DATE - INTERVAL '3 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 4, 3654, 152, 397.89, 4, 2.63, 99.47),
(CURRENT_DATE - INTERVAL '4 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 4, 3789, 163, 426.78, 5, 3.07, 85.36),
(CURRENT_DATE - INTERVAL '5 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 4, 3678, 155, 405.43, 4, 2.58, 101.36),
(CURRENT_DATE - INTERVAL '6 day', 3, 'SCARE Solar - Search', '098-765-4321', 'SCARE Bing Ads', 4, 3876, 167, 437.89, 5, 2.99, 87.58);

-- Insert sample Matomo data for the last 7 days
INSERT INTO public.sm_fact_matomo
(date, campaign_id, campaign_name, site_id, site_name, location_id, visits, unique_visitors, bounce_rate, page_views, pages_per_visit, avg_time_on_site, goal_conversions, goal_conversion_rate)
VALUES
-- All campaigns - Alberta
(CURRENT_DATE - INTERVAL '0 day', 1, 'SCARE Solar - Search', 1, 'SCARE Solar Website', 1, 567, 432, 35.67, 1876, 3.31, 154.32, 22, 3.88),
(CURRENT_DATE - INTERVAL '1 day', 1, 'SCARE Solar - Search', 1, 'SCARE Solar Website', 1, 598, 452, 34.21, 1987, 3.32, 157.65, 25, 4.18),
(CURRENT_DATE - INTERVAL '2 day', 1, 'SCARE Solar - Search', 1, 'SCARE Solar Website', 1, 543, 415, 36.78, 1765, 3.25, 149.87, 20, 3.68),
(CURRENT_DATE - INTERVAL '3 day', 1, 'SCARE Solar - Search', 1, 'SCARE Solar Website', 1, 523, 398, 37.43, 1698, 3.25, 146.54, 18, 3.44),
(CURRENT_DATE - INTERVAL '4 day', 1, 'SCARE Solar - Search', 1, 'SCARE Solar Website', 1, 556, 421, 36.12, 1823, 3.28, 151.23, 21, 3.78),
(CURRENT_DATE - INTERVAL '5 day', 1, 'SCARE Solar - Search', 1, 'SCARE Solar Website', 1, 534, 407, 36.89, 1734, 3.25, 147.90, 19, 3.56),
(CURRENT_DATE - INTERVAL '6 day', 1, 'SCARE Solar - Search', 1, 'SCARE Solar Website', 1, 567, 430, 35.54, 1865, 3.29, 153.67, 23, 4.06);

-- Insert sample RedTrack data for the last 7 days
INSERT INTO public.sm_fact_redtrack
(date, campaign_id, campaign_name, tracker_id, location_id, clicks, conversions, conversion_rate, revenue, profit, roi, leads, sales, lead_to_sale_rate)
VALUES
-- Affiliate Campaign - Arizona (Last 7 days)
(CURRENT_DATE - INTERVAL '0 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 4, 187, 7, 3.74, 2345.67, 987.65, 42.10, 15, 7, 46.67),
(CURRENT_DATE - INTERVAL '1 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 4, 198, 8, 4.04, 2456.78, 1032.45, 42.03, 17, 8, 47.06),
(CURRENT_DATE - INTERVAL '2 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 4, 176, 6, 3.41, 2198.43, 921.54, 41.92, 13, 6, 46.15),
(CURRENT_DATE - INTERVAL '3 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 4, 165, 5, 3.03, 2087.65, 876.32, 41.98, 12, 5, 41.67),
(CURRENT_DATE - INTERVAL '4 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 4, 182, 7, 3.85, 2289.34, 962.32, 42.04, 14, 7, 50.00),
(CURRENT_DATE - INTERVAL '5 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 4, 174, 6, 3.45, 2154.32, 905.67, 42.04, 13, 6, 46.15),
(CURRENT_DATE - INTERVAL '6 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 4, 189, 8, 4.23, 2398.54, 1009.87, 42.10, 16, 8, 50.00),

-- Affiliate Campaign - Washington (Last 7 days)
(CURRENT_DATE - INTERVAL '0 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 6, 143, 5, 3.50, 1876.54, 789.65, 42.08, 11, 5, 45.45),
(CURRENT_DATE - INTERVAL '1 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 6, 156, 6, 3.85, 1987.65, 836.54, 42.09, 13, 6, 46.15),
(CURRENT_DATE - INTERVAL '2 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 6, 134, 4, 2.99, 1765.43, 741.87, 42.02, 10, 4, 40.00),
(CURRENT_DATE - INTERVAL '3 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 6, 125, 4, 3.20, 1654.32, 695.43, 42.04, 9, 4, 44.44),
(CURRENT_DATE - INTERVAL '4 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 6, 137, 5, 3.65, 1832.76, 770.54, 42.04, 11, 5, 45.45),
(CURRENT_DATE - INTERVAL '5 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 6, 129, 4, 3.10, 1732.43, 728.32, 42.04, 10, 4, 40.00),
(CURRENT_DATE - INTERVAL '6 day', 4, 'SCARE Solar - Affiliate', 'RT-4', 6, 147, 6, 4.08, 1932.65, 813.21, 42.08, 12, 6, 50.00);
