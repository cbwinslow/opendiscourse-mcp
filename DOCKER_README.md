# OpenStates.org Database Docker Hub Deployment

This directory contains everything you need to deploy the OpenStates.org database to Docker Hub.

## 🚀 Quick Start

### 1. Set up Docker credentials
```bash
export DOCKER_USERNAME="your-docker-username"
export DOCKER_TOKEN="your-docker-access-token"
```

### 2. Run the automated script
```bash
python3 docker_push_openstates.py --username $DOCKER_USERNAME --token $DOCKER_TOKEN
```

### 3. Manual deployment (alternative)
```bash
# Build and run locally
docker build -t your-username/openstates-database:latest .
docker run -d -p 8080:8080 --name openstates-db your-username/openstates-database:latest

# Or use docker-compose
docker-compose up -d
```

## 📋 Files Created

The script will create these files in your current directory:

- `Dockerfile` - Multi-stage Docker build configuration
- `requirements.txt` - Python dependencies
- `server.py` - Flask API server
- `docker-compose.yml` - Easy deployment configuration
- `deploy.sh` - Quick deployment script
- `README.md` - Documentation
- `.github/workflows/docker-push.yml` - GitHub Actions workflow

## 📡 API Endpoints

Once deployed, the API provides:

- **GET** `/health` - Health check
- **GET** `/api/data` - List available data files
- **GET** `/data/<filename>` - Download specific data file

Available files:
- `legislators.json` - All legislators
- `bills.json` - All bills  
- `committees.json` - All committees
- `events.json` - All events

## 🔄 Automated Updates

The system includes:
- **Daily data updates** via GitHub Actions cron
- **Automated Docker builds** on push/schedule
- **Health monitoring** with built-in checks
- **Metadata tracking** with download timestamps

## 🐳 Docker Hub Features

- **Multi-stage builds** for optimized images
- **Health checks** for monitoring
- **Proper tagging** and versioning
- **Security best practices** with non-root user

## 📊 Data Source

- **Source**: OpenStates.org
- **Update Frequency**: Daily (2 AM UTC)
- **Format**: JSON
- **License**: Check OpenStates.org usage policy

## 🔧 Configuration

You can customize the deployment by modifying:
- Docker repository name (default: `openstates-database`)
- Exposed ports (default: `8080`)
- Update schedule (default: daily at 2 AM UTC)
- Data retention policies

## 📞 Support

For issues:
1. Check the script output for error messages
2. Verify Docker Hub credentials
3. Ensure you have Docker installed and running
4. Check network connectivity to openstates.org

## 🔒 Security Notes

- Store Docker tokens securely (use environment variables)
- Regularly rotate Docker Hub tokens
- Monitor for unauthorized access attempts
- Keep base images updated

## 📈 Monitoring

The deployment includes:
- Container health checks
- API response monitoring
- Data freshness tracking
- Error logging and reporting