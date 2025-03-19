FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pandas sqlalchemy psycopg2-binary google-ads python-dotenv schedule

# Copy the application code
COPY . .

# Copy the entry point script and make it executable
COPY docker_entrypoint.sh /docker_entrypoint.sh
RUN chmod +x /docker_entrypoint.sh

ENTRYPOINT ["/docker_entrypoint.sh"]

# Default command (can be overridden)
CMD ["etl", "7"]
