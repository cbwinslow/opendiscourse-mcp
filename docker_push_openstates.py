#!/usr/bin/env python3
"""
Docker Hub Push Script for OpenStates.org Database
Automates the process of pushing OpenStates.org database to Docker Hub
"""

import os
import sys
import json
import requests
import docker
import tarfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import subprocess

class OpenStatesDockerPusher:
    """Handles pushing OpenStates.org database to Docker Hub"""
    
    def __init__(self, docker_username=None, docker_token=None, repo_name=None):
        self.docker_username = docker_username or os.getenv('DOCKER_USERNAME')
        self.docker_token = docker_token or os.getenv('DOCKER_TOKEN')
        self.repo_name = repo_name or os.getenv('DOCKER_REPO_NAME', 'openstates-database')
        
        if not all([self.docker_username, self.docker_token]):
            print("❌ Error: Docker credentials not provided")
            print("Set DOCKER_USERNAME and DOCKER_TOKEN environment variables")
            print("Or pass them as arguments")
            sys.exit(1)
    
    def download_openstates_data(self, output_dir="openstates_data"):
        """Download OpenStates.org database"""
        print("📥 Downloading OpenStates.org database...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Download latest OpenStates.org database dump
            urls = [
                "https://openstates.org/data/latest/legislators.json",
                "https://openstates.org/data/latest/bills.json", 
                "https://openstates.org/data/latest/committees.json",
                "https://openstates.org/data/latest/events.json"
            ]
            
            for url in urls:
                filename = url.split('/')[-1]
                filepath = os.path.join(output_dir, filename)
                
                print(f"  📥 Downloading {filename}...")
                response = requests.get(url, stream=True, timeout=300)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"  ✅ Downloaded {filename}")
            
            # Create metadata file
            metadata = {
                "download_date": datetime.now().isoformat(),
                "source": "OpenStates.org",
                "version": "latest",
                "files": [url.split('/')[-1] for url in urls]
            }
            
            with open(os.path.join(output_dir, "metadata.json"), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ OpenStates.org data downloaded to {output_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Error downloading OpenStates.org data: {e}")
            return False
    
    def create_dockerfile(self, base_dir):
        """Create Dockerfile for OpenStates.org database"""
        dockerfile_content = """FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \\
    python3-pip \\
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy OpenStates.org data
COPY openstates_data/ /app/openstates_data/

# Create simple web server to serve data
COPY server.py /app/server.py

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run the server
CMD ["python", "server.py"]
"""
        
        with open(os.path.join(base_dir, "Dockerfile"), 'w') as f:
            f.write(dockerfile_content)
        
        # Create requirements.txt
        requirements = """flask==2.3.3
flask-cors==4.0.0
requests==2.31.0
gunicorn==21.2.0
"""
        
        with open(os.path.join(base_dir, "requirements.txt"), 'w') as f:
            f.write(requirements)
        
        # Create simple Flask server
        server_code = """from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/data')
def list_data():
    data_dir = '/app/openstates_data'
    files = []
    if os.path.exists(data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    return jsonify({"files": files})

@app.route('/data/<filename>')
def serve_data(filename):
    data_dir = '/app/openstates_data'
    return send_from_directory(data_dir, filename)

@app.route('/')
def index():
    return '''
    <h1>OpenStates.org Database API</h1>
    <p>Available endpoints:</p>
    <ul>
        <li><a href="/health">Health Check</a></li>
        <li><a href="/api/data">Data List</a></li>
        <li><a href="/data/legislators.json">Legislators</a></li>
        <li><a href="/data/bills.json">Bills</a></li>
        <li><a href="/data/committees.json">Committees</a></li>
        <li><a href="/data/events.json">Events</a></li>
    </ul>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
"""
        
        with open(os.path.join(base_dir, "server.py"), 'w') as f:
            f.write(server_code)
        
        print("✅ Docker configuration files created")
    
    def build_docker_image(self, build_context):
        """Build Docker image"""
        print("🐳 Building Docker image...")
        
        try:
            # Initialize Docker client
            client = docker.from_env()
            
            # Build image
            image, build_logs = client.images.build(
                path=build_context,
                dockerfile="Dockerfile",
                tag=f"{self.docker_username}/{self.repo_name}:latest",
                rm=True,
                forcerm=True
            )
            
            print("✅ Docker image built successfully")
            return image
            
        except Exception as e:
            print(f"❌ Error building Docker image: {e}")
            return None
    
    def push_to_docker_hub(self, image):
        """Push image to Docker Hub"""
        print("📤 Pushing to Docker Hub...")
        
        try:
            # Login to Docker Hub
            client = docker.from_env()
            client.login(
                username=self.docker_username,
                password=self.docker_token
            )
            
            # Push image
            push_logs = client.images.push(
                f"{self.docker_username}/{self.repo_name}:latest",
                stream=True
            )
            
            for log_line in push_logs:
                if 'status' in log_line:
                    print(f"  📤 {log_line}")
            
            print(f"✅ Successfully pushed to Docker Hub: {self.docker_username}/{self.repo_name}:latest")
            return True
            
        except Exception as e:
            print(f"❌ Error pushing to Docker Hub: {e}")
            return False
    
    def create_docker_compose(self, build_context):
        """Create docker-compose.yml for easy deployment"""
        compose_content = f"""version: '3.8'

services:
  openstates-db:
    build: .
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
    container_name: openstates-database
    image: {self.docker_username}/{self.repo_name}:latest
"""
        
        with open(os.path.join(build_context, "docker-compose.yml"), 'w') as f:
            f.write(compose_content)
        
        print("✅ docker-compose.yml created")
    
    def create_github_actions(self, build_context):
        """Create GitHub Actions workflow for automated builds"""
        workflows_dir = os.path.join(build_context, ".github", "workflows")
        os.makedirs(workflows_dir, exist_ok=True)
        
        workflow_content = f"""name: Build and Push OpenStates Database

on:
  push:
    branches: [ main ]
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{{{ secrets.DOCKER_USERNAME }}}
        password: ${{{{ secrets.DOCKER_TOKEN }}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{{{ secrets.DOCKER_USERNAME }}}/{self.repo_name}:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Update deployment status
      run: |
        echo "🚀 Deployment completed successfully!"
        echo "Image: ${{{{ secrets.DOCKER_USERNAME }}}/{self.repo_name}:latest"
"""
        
        with open(os.path.join(workflows_dir, "docker-push.yml"), 'w') as f:
            f.write(workflow_content)
        
        print("✅ GitHub Actions workflow created")
    
    def create_readme(self, build_context):
        """Create README.md for the Docker repository"""
        readme_content = f"""# OpenStates.org Database Docker Image

This Docker image provides the OpenStates.org legislative database via a simple REST API.

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
git clone <your-repo-url>
cd <your-repo-name>
docker-compose up -d
```

### Using Docker directly

```bash
git clone <your-repo-url>
cd <your-repo-name>
docker build -t {self.docker_username}/{self.repo_name}:latest .
docker run -d -p 8080:8080 --name openstates-db {self.docker_username}/{self.repo_name}:latest
```

## 📡 API Endpoints

Once running, the API is available at `http://localhost:8080`

### Health Check
- **GET** `/health` - Health status

### Data Access
- **GET** `/api/data` - List available data files
- **GET** `/data/<filename>` - Download specific data file

### Available Data Files
- `legislators.json` - All legislators
- `bills.json` - All bills  
- `committees.json` - All committees
- `events.json` - All events

## 🔄 Automated Updates

This image is automatically updated daily with the latest OpenStates.org data.

## 📊 Data Source

- **Source**: OpenStates.org
- **Update Frequency**: Daily
- **Format**: JSON
- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

## 🐳 Docker Hub

- **Repository**: `{self.docker_username}/{self.repo_name}`
- **Image**: `{self.docker_username}/{self.repo_name}:latest`

## 📝 License

This project aggregates data from OpenStates.org. Please check their [data usage policy](https://openstates.org/about/) for licensing information.

## 🤝 Contributing

1. Fork this repository
2. Make your changes
3. Submit a pull request

## 📞 Support

For issues and support:
- Create an issue in this repository
- Check the [OpenStates.org documentation](https://openstates.org/docs/)
"""
        
        with open(os.path.join(build_context, "README.md"), 'w') as f:
            f.write(readme_content)
        
        print("✅ README.md created")
    
    def complete_process(self):
        """Complete the entire process"""
        print("🚀 Starting OpenStates.org Docker Hub deployment process...")
        
        # Create temporary build context
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"📁 Using build context: {temp_dir}")
            
            # Download OpenStates.org data
            if not self.download_openstates_data(temp_dir):
                return False
            
            # Create Docker configuration
            self.create_dockerfile(temp_dir)
            self.create_docker_compose(temp_dir)
            self.create_github_actions(temp_dir)
            self.create_readme(temp_dir)
            
            # Build Docker image
            image = self.build_docker_image(temp_dir)
            if not image:
                return False
            
            # Push to Docker Hub
            if not self.push_to_docker_hub(image):
                return False
            
            # Create deployment script
            deploy_script = f"""#!/bin/bash
# OpenStates.org Database Deployment Script

echo "🚀 Deploying OpenStates.org Database..."

# Stop existing container
docker stop openstates-database 2>/dev/null || true
docker rm openstates-database 2>/dev/null || true

# Pull latest image
docker pull {self.docker_username}/{self.repo_name}:latest

# Run new container
docker run -d \\
    --name openstates-database \\
    -p 8080:8080 \\
    --restart unless-stopped \\
    {self.docker_username}/{self.repo_name}:latest

echo "✅ Deployment completed!"
echo "📡 API available at: http://localhost:8080"
echo "📊 Health check: http://localhost:8080/health"
"""
            
            with open(os.path.join(temp_dir, "deploy.sh"), 'w') as f:
                f.write(deploy_script)
            
            os.chmod(os.path.join(temp_dir, "deploy.sh"), 0o755)
            
            # Copy files to current directory if requested
            current_dir = Path.cwd()
            for file in ["Dockerfile", "requirements.txt", "server.py", "docker-compose.yml", "README.md", "deploy.sh"]:
                src = os.path.join(temp_dir, file)
                dst = os.path.join(current_dir, file)
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    print(f"📋 Copied {file} to current directory")
            
            # Create .github/workflows directory in current directory
            github_dir = Path.cwd() / ".github" / "workflows"
            github_dir.mkdir(parents=True, exist_ok=True)
            
            workflow_src = os.path.join(temp_dir, ".github", "workflows", "docker-push.yml")
            workflow_dst = github_dir / "docker-push.yml"
            if os.path.exists(workflow_src):
                shutil.copy2(workflow_src, workflow_dst)
                print("📋 Copied GitHub Actions workflow")
            
            print("✅ Process completed successfully!")
            print(f"📦 Docker image: {self.docker_username}/{self.repo_name}:latest")
            print(f"🌐 Docker Hub: https://hub.docker.com/r/{self.docker_username}/{self.repo_name}")
            print(f"📋 Repository files created in current directory")
            print(f"🚀 Run './deploy.sh' to deploy or use 'docker-compose up -d'")
            
            return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Push OpenStates.org database to Docker Hub")
    parser.add_argument("--username", help="Docker Hub username")
    parser.add_argument("--token", help="Docker Hub access token")
    parser.add_argument("--repo", help="Docker repository name", default="openstates-database")
    parser.add_argument("--download-only", action="store_true", help="Only download data, don't build/push")
    
    args = parser.parse_args()
    
    # Create pusher instance
    pusher = OpenStatesDockerPusher(
        docker_username=args.username,
        docker_token=args.token,
        repo_name=args.repo
    )
    
    if args.download_only:
        # Only download data
        pusher.download_openstates_data()
    else:
        # Complete process
        pusher.complete_process()

if __name__ == "__main__":
    main()