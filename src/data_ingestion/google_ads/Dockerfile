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
    google-ads==17.0.0 \
    google-auth==2.27.0 \
    google-auth-oauthlib==0.5.3 \
    python-dotenv==1.0.0 \
    schedule==1.2.0 \
    pyyaml==6.0.1

# Copy the application code
COPY . .

# Copy the improved entrypoint script
COPY improved_entrypoint.sh /app/improved_entrypoint.sh

# Make the entry point scripts executable
RUN chmod +x /app/railway_entrypoint.sh && \
    chmod +x /app/improved_entrypoint.sh && \
    # Double check files exist
    ls -la /app/railway_entrypoint.sh && \
    ls -la /app/improved_entrypoint.sh && \
    # Ensure the files have Unix line endings
    sed -i 's/\r$//' /app/railway_entrypoint.sh && \
    sed -i 's/\r$//' /app/improved_entrypoint.sh

# Create log directory
RUN mkdir -p /var/log/google_ads

# Use our improved entrypoint script
ENTRYPOINT ["/bin/bash", "/app/improved_entrypoint.sh"]

# Using schedule as default for cron jobs
CMD ["schedule"]
