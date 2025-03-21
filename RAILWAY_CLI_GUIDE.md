# Railway CLI Guide for SCARE Unified Dashboard

This guide explains how to use the Railway CLI to interact with the SCARE Unified Dashboard project locally, making development and testing easier.

## Installation

Install the Railway CLI using the following command:

```bash
curl -fsSL https://railway.com/install.sh | sh
```

For Windows users with PowerShell:

```powershell
irm https://railway.app/install.ps1 | iex
```

## Linking to the Project

Link your local environment to the Railway project:

```bash
railway link -p d103846e-ee3c-4c6c-906d-952780be754c
```

## Common Commands

### Running Services Locally

Run a service locally using Railway's environment variables:

```bash
railway run python src/api/main.py
```

### Viewing Logs

View logs from your Railway deployment:

```bash
railway logs
```

### Accessing Environment Variables

View all environment variables:

```bash
railway variables
```

Add a new environment variable:

```bash
railway variables set KEY=VALUE
```

### Deploying Changes

Deploy your local changes to Railway:

```bash
railway up
```

### Running Database Migrations

Execute database migrations:

```bash
railway run python -m alembic upgrade head
```

### Testing Database Connectivity

Test database connectivity:

```bash
railway run python -c "import sqlalchemy; import os; engine = sqlalchemy.create_engine(os.environ.get('DATABASE_URL')); conn = engine.connect(); conn.close(); print('Database connection successful!')"
```

### Running the Google Ads ETL Process

Run the Google Ads ETL process once:

```bash
railway run python src/data_ingestion/google_ads/main.py --run-once
```

## Development Workflow

1. **Link to Railway**: Start by linking to the Railway project
2. **Pull Environment Variables**: Get the latest environment variables with `railway variables`
3. **Run Locally**: Use `railway run` to execute your code with Railway's environment
4. **Test Changes**: Test your changes locally before deploying
5. **Deploy**: When ready, deploy your changes with `railway up`

## Troubleshooting

### Connection Issues

If you have connection issues:

```bash
railway logout
railway login
railway link -p d103846e-ee3c-4c6c-906d-952780be754c
```

### Database Issues

If you have database connectivity issues:

```bash
railway run pg_isready -h $PGHOST -p $PGPORT -U $PGUSER
```

### Service Health Check

Run the health check script:

```bash
railway run python health_check.py --base-url http://localhost:8000
```

## Additional Resources

- [Railway CLI Documentation](https://docs.railway.app/develop/cli)
- [Railway Deployment Guide](https://docs.railway.app/deploy/deployments)
- [Railway Environment Variables](https://docs.railway.app/develop/variables)
