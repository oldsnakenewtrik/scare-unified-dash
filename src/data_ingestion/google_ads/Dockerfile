FROM python:3.9-slim

WORKDIR /app

# Install system dependencies first
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install numpy first to ensure compatibility
RUN pip install --no-cache-dir numpy==1.23.5

# Install other dependencies with specific versions
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    pandas==1.5.3 \
    sqlalchemy==1.4.46 \
    psycopg2-binary==2.9.6 \
    google-ads==21.2.0 \
    python-dotenv==1.0.0 \
    schedule==1.2.0

# Copy the application code
COPY . .

# Make the entry point script executable - with extra safety measures
RUN chmod +x /app/railway_entrypoint.sh && \
    # Double check file exists
    ls -la /app/railway_entrypoint.sh && \
    # Ensure the file has Unix line endings
    sed -i 's/\r$//' /app/railway_entrypoint.sh

# Create log directory
RUN mkdir -p /var/log/google_ads

ENTRYPOINT ["/bin/bash", "/app/railway_entrypoint.sh"]

# Using schedule as default for cron jobs
CMD ["schedule"]
