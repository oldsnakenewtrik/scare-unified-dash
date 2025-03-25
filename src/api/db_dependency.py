"""
Database dependency module for FastAPI.
This module provides functions for getting database sessions and other database-related utilities.
"""
import uuid
import logging
from fastapi import HTTPException, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Configure logger
logger = logging.getLogger(__name__)

# Global SessionLocal that will be set from main.py
SessionLocal = None

# Function to set the SessionLocal from outside this module
def set_session_local(session_local):
    global SessionLocal
    SessionLocal = session_local
    logger.info("SessionLocal set in db_dependency module")

# Get a database session
def get_db():
    """
    Dependency function to get a database session.
    This function is used by FastAPI endpoints that need database access.
    """
    if SessionLocal is None:
        # We hit this case when database connection could not be established initially
        # Generate a unique error ID for tracking
        error_id = str(uuid.uuid4())
        logger.error(f"Database connection unavailable. Error ID: {error_id}")
        
        # Still raise an exception to inform the client
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable. Error ID: {error_id}"
        )
    
    db = None
    try:
        db = SessionLocal()
        yield db
    except OperationalError as e:
        # Handle database connection errors
        logger.error(f"Database session error: {str(e)}")
        error_id = str(uuid.uuid4())
        logger.error(f"Error ID: {error_id}")
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error. Error ID: {error_id}"
        )
    except Exception as e:
        # Handle other database errors
        logger.error(f"Database session exception: {str(e)}")
        raise
    finally:
        if db:
            db.close()
