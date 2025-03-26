# Database Connection Troubleshooting Guide for Railway

This guide provides a comprehensive approach to diagnosing and resolving database connection issues in Railway-hosted applications.

## Quick Start

Run the database troubleshooting script to automatically diagnose issues:

```bash
python src/api/db_troubleshooter.py
```

For more options:

```bash
python src/api/db_troubleshooter.py --help
```

To fix common issues automatically:

```bash
python src/api/db_troubleshooter.py --fix
```

## Common Issues and Solutions

### 1. Invalid or Missing DATABASE_URL

**Symptoms:**
- Application fails to start
- Error logs show "No database URL available"
- Connection timeouts

**Solutions:**
- Verify DATABASE_URL is set in Railway environment variables
- Check the format: `postgresql://username:password@hostname:port/database_name`
- Ensure credentials are correct
- Run validation script: `python src/api/validate_railway_db.py`

### 2. Network Connectivity Issues

**Symptoms:**
- Connection timeouts
- "Could not connect to server" errors

**Solutions:**
- Verify the database service is running in Railway
- Check if the database hostname is correct
- Ensure the application and database are in the same Railway project
- Test network connectivity with: `python src/api/railway_db_test.py`

### 3. Authentication Failures

**Symptoms:**
- "Password authentication failed" errors
- Access denied messages

**Solutions:**
- Verify username and password in DATABASE_URL
- Check if the database user has proper permissions
- Reset database password in Railway if necessary

### 4. Missing Tables or Columns

**Symptoms:**
- "Relation does not exist" errors
- "Column does not exist" errors

**Solutions:**
- Run the troubleshooter with fix option: `python src/api/db_troubleshooter.py --fix`
- Manually run migrations: `python src/api/db_init.py`
- Check for missing columns with: `python src/api/validate_railway_db.py --fix`

### 5. SSL Connection Issues

**Symptoms:**
- "SSL SYSCALL error" messages
- "server does not support SSL" errors

**Solutions:**
- Add `sslmode=require` to the connection parameters
- Verify the database URL includes proper SSL configuration
- Check if Railway environment requires SSL connections

## Diagnostic Tools

This repository includes several diagnostic tools to help troubleshoot database connection issues:

1. **db_troubleshooter.py**: Comprehensive diagnostic tool that checks environment variables, network connectivity, database connection, and table/column structure.

2. **railway_db_test.py**: Simple script to test database connectivity in Railway environment.

3. **validate_railway_db.py**: Validates database URL format and connection parameters.

## Step-by-Step Troubleshooting Process

### Step 1: Verify Environment Variables

Check if all required environment variables are set:

```bash
python src/api/db_troubleshooter.py
```

### Step 2: Test Basic Connectivity

Test if the database is reachable:

```bash
python src/api/railway_db_test.py
```

### Step 3: Validate Database Structure

Check if all required tables and columns exist:

```bash
python src/api/validate_railway_db.py
```

### Step 4: Fix Common Issues

Attempt to fix common issues automatically:

```bash
python src/api/db_troubleshooter.py --fix
```

### Step 5: Check Application Logs

Review application logs in Railway for specific error messages:

1. Go to Railway dashboard
2. Select your application
3. Click on "Logs"
4. Filter for "error" or "database"

### Step 6: Restart Services

Sometimes a simple restart can resolve connection issues:

1. Go to Railway dashboard
2. Select your application
3. Click "Restart"
4. Do the same for the database service

## Advanced Troubleshooting

### Database Connection Pooling

If you're experiencing intermittent connection issues, consider implementing connection pooling:

1. Update `db_config.py` to use a connection pool
2. Set appropriate pool size based on your application's needs
3. Implement proper connection release in your code

### Handling Transient Failures

Implement retry logic for transient database failures:

1. Use the `connect_with_retry` function in `db_init.py`
2. Set appropriate retry counts and delays
3. Implement circuit breaker pattern for persistent failures

### Database Monitoring

Set up monitoring to detect and alert on database connection issues:

1. Use the database status endpoint: `/api/database/status`
2. Implement health checks that verify database connectivity
3. Set up alerts for connection failures

## Useful Railway Commands

```bash
# View logs for your application
railway logs

# SSH into your application container
railway ssh

# Run a command in your application container
railway run <command>

# View environment variables
railway vars

# Set an environment variable
railway vars set DATABASE_URL=<value>
```

## Additional Resources

- [Railway PostgreSQL Documentation](https://docs.railway.app/databases/postgresql)
- [PostgreSQL Connection Troubleshooting](https://www.postgresql.org/docs/current/auth-troubleshooting.html)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html)
