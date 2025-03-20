# This is a multi-stage build Dockerfile for the SCARE Unified Dashboard
# This file is specifically for the Railway deployment

# Build stage for the frontend - using a minimal approach
FROM node:16-slim AS frontend-build

WORKDIR /app/frontend

# Configure system for minimal memory usage
ENV NODE_OPTIONS="--max-old-space-size=1024 --gc-interval=100"
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

# Build stage for the backend
FROM python:3.9-slim AS backend-build

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies with memory optimization
RUN pip install --no-cache-dir -r requirements.txt --no-deps && \
    pip install --no-cache-dir protobuf==3.19.5

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
