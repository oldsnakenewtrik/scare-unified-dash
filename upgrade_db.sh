#!/bin/bash
# Database upgrade script to run all migration steps

echo "Starting database upgrade..."

# Check if PGPASSWORD is set in environment or .env file
if [ -z "$PGPASSWORD" ]; then
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    else
        echo "Error: PGPASSWORD not set and .env file not found"
        exit 1
    fi
fi

# Set default values if not in environment
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-postgres}
DB_USER=${DB_USER:-postgres}

echo "Connecting to database: $DB_NAME on $DB_HOST:$DB_PORT as $DB_USER"

# Run schema update for network fields
echo "Updating tables to include network fields..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "01_create_tables.sql" || { echo "Failed to update tables"; exit 1; }

# Run view updates to include network information
echo "Updating views with network information..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "02_create_views.sql" || { echo "Failed to update views"; exit 1; }

# Run migration to update existing campaign mappings
echo "Updating existing campaign mappings with network information..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "migrations/03_add_network_to_mappings.sql" || { echo "Failed to run migration"; exit 1; }

echo "Database upgrade completed successfully!"
