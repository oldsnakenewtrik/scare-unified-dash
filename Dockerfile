# This is a multi-stage build Dockerfile for the SCARE Unified Dashboard
# This file is specifically for the Railway deployment

# Build stage for the application
FROM python:3.9-slim AS build

WORKDIR /app

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

# Copy from build stage
COPY --from=build /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /app /app

# Create data directory if it doesn't exist in the final stage
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=5000

# Expose the port
EXPOSE 5000

# Copy the entrypoint script
COPY docker_entrypoint.sh /app/docker_entrypoint.sh
RUN chmod +x /app/docker_entrypoint.sh

# Command to run
ENTRYPOINT ["/app/docker_entrypoint.sh"]
