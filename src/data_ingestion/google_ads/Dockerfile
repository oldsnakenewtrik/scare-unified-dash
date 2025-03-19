FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pandas sqlalchemy psycopg2-binary google-ads python-dotenv schedule

# Copy the application code
COPY . .

# Make the entry point script executable
RUN chmod +x /app/railway_entrypoint.sh

ENTRYPOINT ["/app/railway_entrypoint.sh"]

# Default command (can be overridden)
CMD ["etl", "7"]
