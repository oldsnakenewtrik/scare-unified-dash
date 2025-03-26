#!/bin/bash
# Custom build script for Railway

set -e
echo "Starting custom build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --no-cache-dir sqlalchemy==1.4.46 psycopg2-binary==2.9.6 pandas==1.5.3
pip install --no-cache-dir google-ads==17.0.0 bingads==13.0.16 requests==2.31.0
pip install --no-cache-dir google-auth==2.27.0 google-auth-oauthlib==0.4.6 protobuf==3.19.5
pip install --no-cache-dir python-dotenv==1.0.0 pyyaml==6.0.1 schedule==1.2.0
pip install --no-cache-dir fastapi==0.110.0 uvicorn==0.28.0 pydantic==2.6.1 starlette==0.36.3 loguru==0.7.2

# Build frontend
echo "Building frontend..."
# Instead of cd, use the full path with npm
npm --prefix ./src/frontend ci --production --no-optional
npm --prefix ./src/frontend run build

echo "Build completed successfully!"
