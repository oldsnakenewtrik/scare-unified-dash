"""
Script to inject sample campaign data into the database for testing.
This will add unmapped campaigns by inserting data into the fact tables without mapping entries.
"""
import os
import logging
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("inject_data")

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")

def inject_unmapped_campaigns():
    """Inject sample campaigns that are not mapped yet"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # First, get existing campaign IDs to avoid duplicates
            existing_google_campaign_ids = "SELECT campaign_id FROM sm_fact_google_ads"
            existing_google_ids = set(row[0] for row in conn.execute(text(existing_google_campaign_ids)))
            
            existing_bing_campaign_ids = "SELECT campaign_id FROM sm_fact_bing_ads"
            existing_bing_ids = set(row[0] for row in conn.execute(text(existing_bing_campaign_ids)))
            
            # Now inject new unmapped Google Ads campaigns
            if '98765' not in existing_google_ids:
                logger.info("Injecting unmapped Google Ads campaigns")
                conn.execute(text("""
                    INSERT INTO public.sm_fact_google_ads
                        (date, campaign_id, campaign_name, impressions, clicks, cost, conversions)
                    VALUES
                        ('2025-03-10', '98765', 'Unmapped Google Shopping Campaign', 3500, 420, 890.50, 22),
                        ('2025-03-11', '98765', 'Unmapped Google Shopping Campaign', 3800, 445, 920.75, 25),
                        ('2025-03-10', '112233', 'Display Campaign - Remarketing', 12000, 210, 350.25, 8),
                        ('2025-03-11', '112233', 'Display Campaign - Remarketing', 12500, 230, 370.50, 9)
                """))
                logger.info("Unmapped Google Ads campaigns injected")
            
            # Inject unmapped Bing Ads campaigns
            if 'BNG98765' not in existing_bing_ids:
                logger.info("Injecting unmapped Bing Ads campaigns")
                conn.execute(text("""
                    INSERT INTO public.sm_fact_bing_ads
                        (date, campaign_id, campaign_name, impressions, clicks, cost, conversions)
                    VALUES
                        ('2025-03-10', 'BNG98765', 'Bing Shopping Campaign', 800, 95, 180.50, 6),
                        ('2025-03-11', 'BNG98765', 'Bing Shopping Campaign', 850, 100, 190.75, 7),
                        ('2025-03-10', 'BNG112233', 'Bing Display Campaign', 2500, 150, 220.25, 4),
                        ('2025-03-11', 'BNG112233', 'Bing Display Campaign', 2700, 160, 235.50, 5)
                """))
                logger.info("Unmapped Bing Ads campaigns injected")
            
            # Inject unmapped RedTrack campaigns
            logger.info("Injecting unmapped RedTrack campaigns")
            conn.execute(text("""
                INSERT INTO public.sm_fact_redtrack
                    (date, campaign_id, campaign_name, clicks, conversions, revenue, cost)
                VALUES
                    ('2025-03-10', 'RT_NATIVE', 'Native Ads Campaign', 500, 35, 1750.00, 700.00),
                    ('2025-03-11', 'RT_NATIVE', 'Native Ads Campaign', 550, 40, 2000.00, 750.00),
                    ('2025-03-10', 'RT_TIKTOK', 'TikTok Prospecting', 800, 20, 1200.00, 900.00),
                    ('2025-03-11', 'RT_TIKTOK', 'TikTok Prospecting', 850, 25, 1500.00, 950.00)
            """))
            logger.info("Unmapped RedTrack campaigns injected")
            
            # Inject unmapped Matomo campaigns
            logger.info("Injecting unmapped Matomo campaigns")
            conn.execute(text("""
                INSERT INTO public.sm_fact_matomo
                    (date, campaign_id, campaign_name, visits, bounces, conversions, revenue)
                VALUES
                    ('2025-03-10', 'MT_EMAIL', 'Email Newsletter', 1500, 300, 45, 2250.00),
                    ('2025-03-11', 'MT_EMAIL', 'Email Newsletter', 1600, 320, 48, 2400.00),
                    ('2025-03-10', 'MT_SOCIAL', 'Social Media Traffic', 3000, 900, 25, 1250.00),
                    ('2025-03-11', 'MT_SOCIAL', 'Social Media Traffic', 3200, 960, 28, 1400.00)
            """))
            logger.info("Unmapped Matomo campaigns injected")
            
            conn.commit()
            logger.info("All sample unmapped campaigns injected successfully")
            
            # Check if we have unmapped campaigns now
            check_query = """
            WITH
                google_unmapped AS (
                    SELECT DISTINCT 
                        'Google Ads' as source_system,
                        g.campaign_id as external_campaign_id,
                        g.campaign_name as campaign_name
                    FROM 
                        sm_fact_google_ads g
                    LEFT JOIN 
                        sm_campaign_name_mapping m ON 
                        CAST(g.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                        m.source_system = 'Google Ads'
                    WHERE 
                        m.id IS NULL
                ),
                bing_unmapped AS (
                    SELECT DISTINCT 
                        'Bing Ads' as source_system,
                        b.campaign_id as external_campaign_id,
                        b.campaign_name as campaign_name
                    FROM 
                        sm_fact_bing_ads b
                    LEFT JOIN 
                        sm_campaign_name_mapping m ON 
                        CAST(b.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                        m.source_system = 'Bing Ads'
                    WHERE 
                        m.id IS NULL
                ),
                redtrack_unmapped AS (
                    SELECT DISTINCT 
                        'RedTrack' as source_system,
                        r.campaign_id as external_campaign_id,
                        r.campaign_name as campaign_name
                    FROM 
                        sm_fact_redtrack r
                    LEFT JOIN 
                        sm_campaign_name_mapping m ON 
                        CAST(r.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                        m.source_system = 'RedTrack'
                    WHERE 
                        m.id IS NULL
                ),
                matomo_unmapped AS (
                    SELECT DISTINCT 
                        'Matomo' as source_system,
                        mt.campaign_id as external_campaign_id,
                        mt.campaign_name as campaign_name
                    FROM 
                        sm_fact_matomo mt
                    LEFT JOIN 
                        sm_campaign_name_mapping m ON 
                        CAST(mt.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                        m.source_system = 'Matomo'
                    WHERE 
                        m.id IS NULL
                )
            SELECT COUNT(*) as total_unmapped
            FROM (
                SELECT * FROM google_unmapped
                UNION ALL
                SELECT * FROM bing_unmapped
                UNION ALL
                SELECT * FROM redtrack_unmapped
                UNION ALL
                SELECT * FROM matomo_unmapped
            ) as all_unmapped
            """
            
            unmapped_count = conn.execute(text(check_query)).scalar()
            logger.info(f"Total unmapped campaigns now: {unmapped_count}")
    
    except Exception as e:
        logger.error(f"Error injecting sample data: {str(e)}")
        raise

if __name__ == "__main__":
    inject_unmapped_campaigns()
