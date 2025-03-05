# This is a multi-stage build Dockerfile for the main API service
# This file is specifically for the Railway deployment

# Build stage for the API
FROM python:3.9-slim AS api-build

WORKDIR /app

COPY src/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/api /app

# Final stage
FROM python:3.9-slim

WORKDIR /app

# Copy from build stage
COPY --from=api-build /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=api-build /app /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=5000

# Expose the port
EXPOSE 5000

# Command to run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
