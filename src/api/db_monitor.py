"""
Database Monitoring Utility for SCARE Unified Dashboard

This script provides utilities for monitoring database connectivity
and managing connection pools in the application.
"""
import os
import time
import logging
import threading
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.pool import QueuePool

logger = logging.getLogger("db_monitor")

class DatabaseMonitor:
    """
    Monitor database connectivity and manage connection pools.
    
    This class provides utilities to:
    1. Periodically check database connectivity
    2. Refresh connections when needed
    3. Provide health status for the application
    """
    
    def __init__(self, database_url, check_interval=60, pool_recycle=300):
        """
        Initialize the database monitor
        
        Args:
            database_url (str): The database connection string
            check_interval (int): How often to check database connectivity in seconds
            pool_recycle (int): Time in seconds after which a connection is recycled
        """
        self.database_url = database_url
        self.check_interval = check_interval
        self.pool_recycle = pool_recycle
        self.engine = None
        self.last_successful_check = None
        self.last_failed_check = None
        self.consecutive_failures = 0
        self.is_running = False
        self.monitor_thread = None
        self.status = {
            "status": "initializing",
            "last_check": None,
            "consecutive_failures": 0,
            "is_connected": False
        }
        
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Create a new SQLAlchemy engine with appropriate connection pool settings"""
        try:
            logger.info("Initializing database engine")
            # Configure engine with connection pooling
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True
            )
            logger.info("Database engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            self.status["status"] = "initialization_failed"
    
    def check_connectivity(self):
        """Check database connectivity with a simple query"""
        start_time = time.time()
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                elapsed = time.time() - start_time
                
                self.last_successful_check = datetime.now()
                self.consecutive_failures = 0
                
                self.status = {
                    "status": "connected",
                    "last_check": self.last_successful_check.isoformat(),
                    "check_duration_ms": round(elapsed * 1000, 2),
                    "consecutive_failures": 0,
                    "is_connected": True
                }
                
                logger.debug(f"Database connectivity check successful in {elapsed:.2f}s")
                return True
                
        except Exception as e:
            elapsed = time.time() - start_time
            self.last_failed_check = datetime.now()
            self.consecutive_failures += 1
            
            self.status = {
                "status": "disconnected",
                "last_check": self.last_failed_check.isoformat(),
                "check_duration_ms": round(elapsed * 1000, 2),
                "consecutive_failures": self.consecutive_failures,
                "last_error": str(e),
                "is_connected": False
            }
            
            logger.warning(f"Database connectivity check failed: {str(e)}")
            
            # If we have too many consecutive failures, reinitialize the engine
            if self.consecutive_failures >= 3:
                logger.warning(f"Multiple consecutive connection failures ({self.consecutive_failures}), reinitializing engine")
                self._initialize_engine()
            
            return False
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if self.is_running:
            logger.warning("Monitoring thread is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Database monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            logger.info("Database monitoring stopped")
    
    def _monitoring_loop(self):
        """Background thread loop that periodically checks database connectivity"""
        while self.is_running:
            try:
                self.check_connectivity()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
            
            # Sleep for the check interval
            time.sleep(self.check_interval)
    
    def get_status(self):
        """Get the current database connection status"""
        # Force a fresh check if the last check is too old
        if (self.status["status"] == "initializing" or 
            "last_check" not in self.status or 
            self.status["last_check"] is None or
            (datetime.now() - datetime.fromisoformat(self.status["last_check"]) > 
             timedelta(seconds=self.check_interval * 2))):
            self.check_connectivity()
        
        return self.status
    
    def reconnect(self):
        """Force a reconnection by reinitializing the engine"""
        logger.info("Forcing database reconnection")
        self._initialize_engine()
        return self.check_connectivity()

# Global instance that can be imported and used throughout the application
_monitor = None

def initialize_monitor(database_url, check_interval=60, pool_recycle=300, start=True):
    """Initialize the global database monitor instance"""
    global _monitor
    if _monitor is not None:
        logger.warning("Database monitor already initialized")
        return _monitor
    
    _monitor = DatabaseMonitor(
        database_url=database_url,
        check_interval=check_interval,
        pool_recycle=pool_recycle
    )
    
    if start:
        _monitor.start_monitoring()
    
    return _monitor

def get_monitor():
    """Get the global database monitor instance"""
    global _monitor
    if _monitor is None:
        raise RuntimeError("Database monitor not initialized. Call initialize_monitor first.")
    return _monitor

def check_db_connectivity():
    """Utility function to check database connectivity using the global monitor"""
    monitor = get_monitor()
    return monitor.check_connectivity()

def get_db_status():
    """Utility function to get database status using the global monitor"""
    monitor = get_monitor()
    return monitor.get_status()

def force_db_reconnect():
    """Utility function to force database reconnection using the global monitor"""
    monitor = get_monitor()
    return monitor.reconnect()

# Example of usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL") or "postgresql://scare_user:scare_password@localhost:5432/scare_metrics"
    
    # Initialize and start the monitor
    monitor = initialize_monitor(database_url, check_interval=10)
    
    try:
        # Run for 60 seconds, checking status every 5 seconds
        for _ in range(12):
            status = get_db_status()
            print(f"Database Status: {status['status']}")
            if not status['is_connected'] and status['consecutive_failures'] > 2:
                print("Attempting to reconnect...")
                force_db_reconnect()
            time.sleep(5)
    finally:
        # Stop monitoring
        monitor.stop_monitoring()
