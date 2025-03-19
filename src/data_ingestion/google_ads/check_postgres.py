#!/usr/bin/env python

import psycopg2
import logging
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("postgres_check")

def check_host_availability(host, port=5432):
    """Check if a host is reachable on a specific port"""
    logger.info(f"Checking if host {host} is available on port {port}...")
    
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)  # Set timeout to 2 seconds
        
        # Attempt to connect
        result = s.connect_ex((host, port))
        
        # Close the socket
        s.close()
        
        if result == 0:
            logger.info(f"SUCCESS: Host {host} is reachable on port {port}")
            return True
        else:
            logger.error(f"FAILED: Host {host} is NOT reachable on port {port}")
            return False
            
    except socket.error as e:
        logger.error(f"Socket error when checking {host}:{port} - {str(e)}")
        return False

def try_connect_psycopg2(host, port=5432, dbname="postgres", user="postgres", password="postgres"):
    """Try to connect to PostgreSQL using psycopg2"""
    logger.info(f"Trying to connect to PostgreSQL on {host}:{port}...")
    
    try:
        # Connection string
        conn_string = f"host={host} port={port} dbname={dbname} user={user} password={password}"
        
        # Attempt connection
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # Test with a simple query
        cursor.execute("SELECT version();")
        record = cursor.fetchone()
        logger.info(f"Connected to PostgreSQL: {record[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        return False

def main():
    """Main function to check PostgreSQL availability"""
    logger.info("Checking PostgreSQL availability...")
    
    # Check localhost
    host_available = check_host_availability("localhost")
    if host_available:
        try_connect_psycopg2("localhost", user="scare_user", password="scare_password", dbname="scare_metrics")
    
    # Check 127.0.0.1
    host_available = check_host_availability("127.0.0.1")
    if host_available:
        try_connect_psycopg2("127.0.0.1", user="scare_user", password="scare_password", dbname="scare_metrics")
    
    # Check default postgres server
    check_host_availability("postgres")
    
    logger.info("PostgreSQL availability check completed")

if __name__ == "__main__":
    main()
