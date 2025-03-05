from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
import datetime
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="SCARE Unified Metrics API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://front-production-f6e6.up.railway.app", "*"],  # Allow your frontend domain and all origins during development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for API response
class MetricsSummary(BaseModel):
    date: datetime.date
    total_clicks: int
    total_impressions: int
    total_cost: float
    total_conversions: float
    total_revenue: float
    website_visitors: int
    salesforce_leads: int
    opportunities: int
    closed_won: int

class DateRangeParams(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    campaign_name: Optional[str] = None
    source_system: Optional[str] = None

class CampaignMetrics(BaseModel):
    campaign_id: int
    campaign_name: str
    source_system: str
    is_active: bool
    date: datetime.date
    impressions: int
    clicks: int
    spend: float
    revenue: float
    conversions: float
    cpc: float
    smooth_leads: int
    total_sales: int
    users: int

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now()}

# API endpoints
@app.get("/api/metrics/summary", response_model=List[MetricsSummary])
def get_metrics_summary(start_date: datetime.date, end_date: datetime.date, db=Depends(get_db)):
    """
    Get unified metrics summary for a given date range
    """
    try:
        query = text("""
            SELECT 
                full_date as date,
                SUM(total_clicks) as total_clicks,
                SUM(total_impressions) as total_impressions,
                SUM(total_cost) as total_cost,
                SUM(total_conversions) as total_conversions,
                SUM(total_revenue) as total_revenue,
                SUM(website_visitors) as website_visitors,
                SUM(salesforce_leads) as salesforce_leads,
                SUM(salesforce_opportunities) as opportunities,
                SUM(salesforce_closed_won) as closed_won
            FROM view_unified_metrics
            WHERE full_date BETWEEN :start_date AND :end_date
            GROUP BY full_date
            ORDER BY full_date
        """)
        
        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        metrics = [dict(row) for row in result]
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/metrics/by-source")
def get_metrics_by_source(start_date: datetime.date, end_date: datetime.date, db=Depends(get_db)):
    """
    Get metrics broken down by source system
    """
    try:
        query = text("""
            SELECT 
                source_system,
                SUM(total_clicks) as total_clicks,
                SUM(total_impressions) as total_impressions,
                SUM(total_cost) as total_cost,
                SUM(total_conversions) as total_conversions,
                SUM(total_revenue) as total_revenue
            FROM view_unified_metrics
            WHERE full_date BETWEEN :start_date AND :end_date
            GROUP BY source_system
            ORDER BY source_system
        """)
        
        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        metrics = [dict(row) for row in result]
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/metrics/by-campaign")
def get_metrics_by_campaign(start_date: datetime.date, end_date: datetime.date, db=Depends(get_db)):
    """
    Get metrics broken down by campaign
    """
    try:
        query = text("""
            SELECT 
                campaign_name,
                source_system,
                SUM(total_clicks) as total_clicks,
                SUM(total_impressions) as total_impressions,
                SUM(total_cost) as total_cost,
                SUM(total_conversions) as total_conversions,
                SUM(total_revenue) as total_revenue
            FROM view_unified_metrics
            WHERE full_date BETWEEN :start_date AND :end_date
            GROUP BY campaign_name, source_system
            ORDER BY campaign_name, source_system
        """)
        
        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        metrics = [dict(row) for row in result]
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/campaigns/metrics", response_model=List[CampaignMetrics])
def get_campaigns_metrics(db=Depends(get_db)):
    """
    Get all campaign metrics for the master tab view.
    """
    try:
        query = text("""
            SELECT 
                dc.campaign_id,
                dc.campaign_name,
                dc.source_system,
                dc.is_active,
                um.date,
                um.impressions,
                um.clicks,
                um.cost,
                um.conversions,
                um.revenue,
                um.cpc,
                COALESCE(sl.smooth_leads, 0) as smooth_leads,
                COALESCE(ts.total_sales, 0) as total_sales
            FROM scare_metrics.dim_campaign dc
            LEFT JOIN scare_metrics.unified_metrics_view um ON dc.campaign_id = um.campaign_id
            LEFT JOIN (
                SELECT campaign_id, SUM(leads) as smooth_leads
                FROM scare_metrics.fact_leads
                GROUP BY campaign_id
            ) sl ON dc.campaign_id = sl.campaign_id
            LEFT JOIN (
                SELECT campaign_id, COUNT(*) as total_sales
                FROM scare_metrics.fact_sales
                GROUP BY campaign_id
            ) ts ON dc.campaign_id = ts.campaign_id
        """)
        
        result = db.execute(query)
        
        data = []
        for row in result:
            data.append({
                "campaign_id": row.campaign_id,
                "campaign_name": row.campaign_name,
                "source_system": row.source_system,
                "is_active": row.is_active,
                "date": row.date.isoformat() if row.date else None,
                "impressions": row.impressions or 0,
                "clicks": row.clicks or 0,
                "spend": float(row.cost) if row.cost else 0,
                "revenue": float(row.revenue) if row.revenue else 0,
                "conversions": float(row.conversions) if row.conversions else 0,
                "cpc": float(row.cpc) if row.cpc else 0,
                "smooth_leads": row.smooth_leads or 0,
                "total_sales": row.total_sales or 0,
                "users": 0  # Placeholder for now, could be populated from matomo data
            })
        
        return data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
