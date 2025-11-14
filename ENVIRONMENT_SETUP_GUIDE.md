# OpenDiscourse Environment Setup Guide

## Overview

This guide provides comprehensive instructions for setting up the OpenDiscourse environment for data ingestion and monitoring.

## Prerequisites

- Python 3.8+ (recommended: Python 3.14)
- PostgreSQL 12+ (recommended: PostgreSQL 16)
- Git
- Internet access for API connections

## Environment Variables

### Required Environment Variables

Create a `.env` file in `/home/cbwinslow/opendiscourse/mcp_server/` with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database_name

# API Keys
CONGRESS_API_KEY=your_congress_gov_api_key
GOVINFO_API_KEY=your_govinfo_api_key  
OPENSTATES_API_KEY=your_openstates_api_key
```

### API Key Setup

#### Congress.gov API
1. Visit [api.congress.gov](https://api.congress.gov/)
2. Sign up for an API key
3. Add to `.env` file as `CONGRESS_API_KEY`

#### GovInfo API
1. Visit [api.govinfo.gov](https://api.govinfo.gov/)
2. Request an API key
3. Add to `.env` file as `GOVINFO_API_KEY`

#### OpenStates API
1. Visit [openstates.org](https://openstates.org/api/)
2. Sign up for an API key
3. Add to `.env` file as `OPENSTATES_API_KEY`

## Database Setup

### PostgreSQL Configuration

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # macOS with Homebrew
   brew install postgresql
   brew services start postgresql
   ```

2. **Create Database**:
   ```sql
   CREATE DATABASE opendiscourse;
   CREATE USER opendiscourse WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE opendiscourse TO opendiscourse;
   ```

3. **Set DATABASE_URL**:
   ```bash
   DATABASE_URL=postgresql://opendiscourse:your_secure_password@localhost:5432/opendiscourse
   ```

### Database Schema

The database schema is automatically created by running the schema verification script:

```bash
cd /home/cbwinslow/opendiscourse
export DATABASE_URL=postgresql://opendiscourse:password@host:5432/opendiscourse
python3 verify_database_schema.py
```

This will create:
- **68 tables** including congress_bills, congress_members, etc.
- **18 triggers** for progress tracking and data quality
- **7 functions** for monitoring and job management
- **286 indexes** for performance optimization

## Python Dependencies

### System Requirements

Install required system packages:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-venv build-essential libpq-dev

# macOS with Homebrew
brew install postgresql libpq
```

### Python Packages

Install required Python packages:

```bash
cd /home/cbwinslow/opendiscourse

# Option 1: Install from requirements.txt
pip install -r requirements.txt

# Option 2: Install key packages manually
pip install psycopg2-binary sqlalchemy pandas requests
pip install python-dotenv beautifulsoup4 lxml
```

## Project Structure

```
opendiscourse/
├── mcp_server/
│   ├── .env                    # Environment variables
│   ├── db.py                   # Database connection utilities
│   ├── main.py                 # Main application entry point
│   ├── clients/                # API client modules
│   │   ├── congress_client.py
│   │   ├── govinfo_client.py
│   │   └── openstates_client.py
│   ├── scripts/                # Ingestion scripts
│   │   ├── congress_ingest.py
│   │   ├── congress_members_ingest.py
│   │   └── ...
│   ├── sql/                    # Database schema files
│   │   ├── congress_schema_fixed.sql
│   │   ├── monitoring_triggers.sql
│   │   └── ...
│   └── utils/                  # Utility modules
│       ├── ingest.py
│       ├── monitoring.py
│       └── ...
├── tests/                      # Test suite
├── monitoring/                 # Monitoring configuration
└── docs/                      # Documentation
```

## Verification Steps

### 1. Environment Verification

```bash
cd /home/cbwinslow/opendiscourse
python3 verify_api_keys.py
```

Expected output:
```
🎉 ALL API KEYS VERIFIED AND WORKING!
✅ Ready for data ingestion
```

### 2. Database Verification

```bash
python3 verify_database_schema.py
```

Expected output:
```
🎉 DATABASE SCHEMA IS READY FOR INGESTION!
```

### 3. Connectivity Verification

```bash
python3 test_database_connectivity_simple.py
```

Expected output:
```
✅ All systems operational!
```

### 4. End-to-End Verification

```bash
python3 comprehensive_test.py
```

Expected output:
```
🎉 EXCELLENT - System ready for production!
```

## Running Ingestion

### Basic Ingestion Commands

```bash
# Set environment
export DATABASE_URL=postgresql://opendiscourse:password@host:5432/opendiscourse
source /home/cbwinslow/opendiscourse/mcp_server/.env

# Run ingestion scripts
python3 mcp_server/scripts/congress_ingest.py
python3 mcp_server/scripts/congress_members_ingest.py
python3 mcp_server/scripts/congress_comprehensive_ingest.py
```

### Monitoring Ingestion

```bash
# Check ingestion jobs
python3 -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
cursor = conn.cursor()
cursor.execute('SELECT * FROM get_ingestion_alerts()')
for alert in cursor.fetchall():
    print(alert)
conn.close()
"
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```
Error: connection refused
```
**Solution**: Check PostgreSQL is running and DATABASE_URL is correct.

#### 2. API Key Errors
```
Error: 401 Unauthorized
```
**Solution**: Verify API keys are correct and active.

#### 3. Module Import Errors
```
ModuleNotFoundError: No module named 'psycopg2'
```
**Solution**: Install missing Python packages.

#### 4. Permission Errors
```
Error: permission denied for database
```
**Solution**: Check database user permissions.

### Debug Mode

Enable debug logging:

```bash
export PYTHONPATH=/home/cbwinslow/opendiscourse:$PYTHONPATH
export DEBUG=true
```

### Log Files

Check log files for detailed error information:
- Database logs: `/var/log/postgresql/`
- Application logs: Check individual script outputs
- Monitoring logs: `ingestion_performance_log` table

## Performance Optimization

### Database Optimization

1. **Connection Pooling**: The system uses SQLAlchemy connection pooling
2. **Indexing**: 286 indexes are automatically created
3. **Batch Processing**: Scripts process data in batches of 1000 records

### API Rate Limits

- **Congress.gov**: 10 requests/second
- **GovInfo**: 100 requests/hour
- **OpenStates**: 1000 requests/hour

### Monitoring Performance

Monitor system performance using:

```bash
# Check performance logs
python3 -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
cursor = conn.cursor()
cursor.execute('SELECT * FROM ingestion_performance_summary LIMIT 10')
for row in cursor.fetchall():
    print(row)
conn.close()
"
```

## Security Considerations

### API Key Security

1. Never commit API keys to version control
2. Use environment variables or secure key management
3. Rotate API keys regularly
4. Monitor API usage for unusual activity

### Database Security

1. Use strong passwords
2. Limit database user permissions
3. Enable SSL connections in production
4. Regular database backups

## Production Deployment

### Environment Configuration

For production deployment:

1. **Use environment-specific .env files**
2. **Enable SSL for database connections**
3. **Set up proper logging**
4. **Configure monitoring and alerting**
5. **Set up automated backups**

### Scaling Considerations

1. **Database**: Consider read replicas for high read loads
2. **API Clients**: Implement proper rate limiting and retry logic
3. **Monitoring**: Set up comprehensive monitoring and alerting
4. **Backups**: Automated daily database backups

## Support

### Getting Help

1. Check the troubleshooting section above
2. Review log files for detailed error messages
3. Run verification scripts to identify issues
4. Check API documentation for rate limits and usage guidelines

### Documentation

- API Documentation: Links provided in API Key Setup section
- Database Schema: See `mcp_server/sql/` directory
- Script Documentation: See individual script headers
- Monitoring: See `monitoring/` directory

---

**Last Updated**: November 14, 2025
**Version**: 1.0
**Status**: Production Ready ✅