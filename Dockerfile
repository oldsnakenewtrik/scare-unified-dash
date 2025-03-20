# This is a multi-stage build Dockerfile for the SCARE Unified Dashboard
# This file is specifically for the Railway deployment

# Build stage for the frontend
FROM node:16-alpine AS frontend-build

WORKDIR /app/frontend

# Copy frontend package.json and install dependencies
COPY src/frontend/package*.json ./
RUN npm ci

# Copy frontend source code and build
COPY src/frontend/ ./
COPY src/frontend/.env.production ./.env.production
RUN npm run build

# Build stage for the backend
FROM python:3.9-slim AS backend-build

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    pandas==1.5.3 \
    sqlalchemy==1.4.46 \
    psycopg2-binary==2.9.6 \
    google-ads==17.0.0 \
    google-auth==2.27.0 \
    google-auth-oauthlib==0.4.6 \
    python-dotenv==1.0.0 \
    schedule==1.2.0 \
    pyyaml==6.0.1

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
