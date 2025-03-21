# Railway Local Development Helper PowerShell Script
# This script provides shortcuts for common Railway CLI commands

param (
    [Parameter(Position=0)]
    [ValidateSet("setup", "api", "etl", "db", "health", "unmapped", "all", "")]
    [string]$Command = ""
)

if ($Command -eq "") {
    Write-Host "Railway Local Development Helper"
    Write-Host ""
    Write-Host "Usage: .\railway_dev.ps1 [command]"
    Write-Host ""
    Write-Host "Available commands:"
    Write-Host "  setup      - Set up Railway CLI and link to project"
    Write-Host "  api        - Run the API server with Railway environment"
    Write-Host "  etl        - Run the Google Ads ETL process once"
    Write-Host "  db         - Check database connectivity and tables"
    Write-Host "  health     - Check API health"
    Write-Host "  unmapped   - Check for unmapped campaigns"
    Write-Host "  all        - Run all checks"
    Write-Host ""
    exit 1
}

# Run the Python helper script with the provided command
python railway_local.py $Command
