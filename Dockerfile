# This is a multi-stage build Dockerfile for the SCARE Unified Dashboard
# This file is specifically for the Railway deployment

# Build stage for the frontend - using a minimal approach
FROM node:16-slim AS frontend-build

WORKDIR /app/frontend

# Configure system for minimal memory usage - remove invalid gc-interval flag
ENV NODE_OPTIONS="--max-old-space-size=1024"
ENV NPM_CONFIG_LEGACY_PEER_DEPS=true
ENV CI=false

# First just copy package files
COPY src/frontend/package.json ./
COPY src/frontend/package-lock.json ./

# Install dependencies with production flag to reduce memory usage
RUN npm ci --production --prefer-offline --no-audit --no-optional

# Now copy the source code
COPY src/frontend/ ./
COPY src/frontend/.env.production ./.env.production

# Build with reduced parallel processes
RUN npm run build --production

# Build stage for the backend - WITHOUT postgresql-client
FROM python:3.9-slim AS backend-build

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies with memory optimization
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir protobuf==3.20.0 && \
    pip install --no-cache-dir --upgrade --force-reinstall numpy pandas

# Copy the rest of the application
COPY . /app

# Create data directory for JSON files
RUN mkdir -p /app/data

# Final stage - install postgresql-client only here
FROM python:3.9-slim

WORKDIR /app

# Install postgresql-client and procps for ps command
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from build stage
COPY --from=backend-build /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin
COPY --from=backend-build /app /app

# Copy built frontend
COPY --from=frontend-build /app/frontend/build /app/src/frontend/build

# Create data directory if it doesn't exist in the final stage
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=5000

# Expose the port
EXPOSE 5000

# Copy entrypoint script from its new location
COPY scripts/docker_entrypoint.sh /app/docker_entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /app/docker_entrypoint.sh
RUN chmod +x /app/src/data_ingestion/google_ads/railway_entrypoint.sh # Add execute permission for the Google Ads script
RUN chmod +x /app/src/data_ingestion/bing_ads/bads_entrypoint.sh # Add execute permission for the Bing Ads script

# Set entrypoint (This is the default, overridden by Railway start command for specific services)
ENTRYPOINT ["/app/docker_entrypoint.sh"]
