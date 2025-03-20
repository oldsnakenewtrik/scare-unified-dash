#!/bin/bash
set -e

# Print environment info (for debugging)
echo "Starting SCARE Unified Dashboard..."
echo "Python path: $PYTHONPATH"
echo "Working directory: $(pwd)"

# Create data directory if it doesn't exist
mkdir -p ./data

# Start Google Ads ETL service in the background
echo "Starting Google Ads ETL service..."
python ./src/data_ingestion/google_ads/main.py --service &
GOOGLE_ADS_PID=$!

# Wait a moment to ensure the service starts
sleep 2

# Check if service started successfully - use kill -0 instead of ps
if kill -0 $GOOGLE_ADS_PID 2>/dev/null; then
    echo "Google Ads ETL service started successfully (PID: $GOOGLE_ADS_PID)"
else
    echo "Warning: Google Ads ETL service failed to start"
fi

# Check PostgreSQL connection using the DATABASE_URL environment variable directly
echo "Checking database connection..."
if python -c "import sqlalchemy, os; print('ENV DATABASE_URL:', os.environ.get('DATABASE_URL') or os.environ.get('RAILWAY_DATABASE_URL')); engine = sqlalchemy.create_engine(os.environ.get('DATABASE_URL') or os.environ.get('RAILWAY_DATABASE_URL')); conn = engine.connect(); conn.close(); print('Database connection successful!')"; then
    echo "Database connection confirmed!"
else
    echo "Warning: Could not connect to database"
fi

# Run database initialization script
echo "Initializing database..."
python ./src/api/db_init.py

# Start the API server
echo "Starting web server..."
cd .
exec uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
