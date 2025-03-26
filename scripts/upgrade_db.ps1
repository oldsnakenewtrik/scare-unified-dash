# Database upgrade script for Windows to run all migration steps

Write-Host "Starting database upgrade..." -ForegroundColor Cyan

# Load environment variables from .env file if it exists
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "Env:$key" -Value $value
        }
    }
}

# Check if required environment variables are set
if (-not $env:PGPASSWORD) {
    Write-Host "Error: PGPASSWORD not set in environment or .env file" -ForegroundColor Red
    exit 1
}

# Set default values if not in environment
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "postgres" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }

Write-Host "Connecting to database: $DB_NAME on $DB_HOST`:$DB_PORT as $DB_USER" -ForegroundColor Green

# Function to run a SQL file
function Run-SqlFile {
    param (
        [string]$FilePath,
        [string]$Description
    )
    
    Write-Host $Description -ForegroundColor Cyan
    
    try {
        & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $FilePath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to execute $FilePath" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "Error executing $FilePath : $_" -ForegroundColor Red
        exit 1
    }
}

# Run schema update for network fields
Run-SqlFile -FilePath "01_create_tables.sql" -Description "Updating tables to include network fields..."

# Run view updates to include network information
Run-SqlFile -FilePath "02_create_views.sql" -Description "Updating views with network information..."

# Run migration to update existing campaign mappings
Run-SqlFile -FilePath "migrations\03_add_network_to_mappings.sql" -Description "Updating existing campaign mappings with network information..."

Write-Host "Database upgrade completed successfully!" -ForegroundColor Green
