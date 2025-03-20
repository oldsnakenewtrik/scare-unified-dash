# This is a multi-stage build Dockerfile for the SCARE Unified Dashboard
# This file is specifically for the Railway deployment

# Build stage for the frontend
FROM node:16-bullseye AS frontend-build

WORKDIR /app/frontend

# Configure npm
RUN npm config set network-timeout 600000 && \
    npm config set fetch-retry-maxtimeout 600000

# Copy frontend package.json and install dependencies
COPY src/frontend/package*.json ./
ENV NODE_OPTIONS="--max-old-space-size=4096"
ENV NPM_CONFIG_LEGACY_PEER_DEPS=true
RUN npm ci --no-audit --prefer-offline

# Copy frontend source code and build
COPY src/frontend/ ./
COPY src/frontend/.env.production ./.env.production
ENV CI=false
RUN npm run build --verbose

# Build stage for the backend
FROM python:3.9-slim AS backend-build

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Create data directory for JSON files
RUN mkdir -p /app/data

# Final stage
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy from backend build stage
COPY --from=backend-build /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin
COPY --from=backend-build /app /app

# Copy built frontend from frontend build stage
COPY --from=frontend-build /app/frontend/build /app/src/frontend/build

# Create data directory if it doesn't exist in the final stage
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=5000

# Expose the port
EXPOSE 5000

# Set the entrypoint script
COPY docker_entrypoint.sh /app/docker_entrypoint.sh
RUN chmod +x /app/docker_entrypoint.sh

# Run the application
ENTRYPOINT ["/app/docker_entrypoint.sh"]
