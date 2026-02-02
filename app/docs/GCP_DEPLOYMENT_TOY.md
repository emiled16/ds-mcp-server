# GCP Deployment Guide - Toy System (Learning/Development)

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Cost Estimation](#cost-estimation)
4. [Deployment Steps](#deployment-steps)
5. [Testing & Usage](#testing--usage)

---

## OVERVIEW

This guide provides a **simplified, cost-effective deployment** for learning and development purposes. Perfect for:
- Learning GCP services
- Testing the application
- Personal projects
- Development environments
- Demos and prototypes

**Key Differences from Production:**
- Single VM instead of Kubernetes cluster
- Docker Compose instead of orchestration
- No auto-scaling or redundancy
- Free tier where possible
- Minimal monitoring
- **Target Cost: $20-50/month** (or free tier)

---

## ARCHITECTURE

```
                     Internet
                        │
                        ▼
              ┌─────────────────┐
              │   Compute VM    │
              │  (e2-medium)    │
              │                 │
              │  ┌───────────┐  │
              │  │ MCP Server│  │
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │  Celery   │  │
              │  │  Worker   │  │
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │  MLflow   │  │
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │  MongoDB  │  │
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │   Redis   │  │
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │PostgreSQL │  │
              │  └───────────┘  │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  Cloud Storage  │
              │  (Free Tier)    │
              └─────────────────┘
```

**All services run in Docker Compose on a single VM!**

---

## NON-FUNCTIONAL REQUIREMENTS (Toy System)

### 1. **Scalability**
- **Not a priority**: Single VM handles light load only
- Target: 1-5 concurrent users
- Max: 10-20 tool calls per minute

### 2. **Performance**
- **Acceptable**: Response times may be slower
- Tool calls: <5 seconds (P95)
- Dataset size limit: <100MB

### 3. **Availability**
- **Best Effort**: No SLA
- Downtime acceptable for maintenance
- Manual restart on failures

### 4. **Durability**
- **Basic**: Manual backups only
- Data loss risk acknowledged
- Backup frequency: Weekly (manual)

### 5. **Security**
- **Basic**: Simple firewall rules
- No VPC peering
- HTTP allowed (HTTPS optional)
- Secrets in environment files

### 6. **Observability**
- **Minimal**: Docker logs only
- No distributed tracing
- Basic health checks

### 7. **Cost**
- **Primary Goal**: Stay within free tier or minimal cost
- Use smallest instance sizes
- No redundancy

---

## COST ESTIMATION

### Monthly Costs (All Free Tier When Possible)

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| **Compute Engine** | 1 x e2-medium (2 vCPU, 4GB RAM, 50GB disk) | ~$25 |
| **Cloud Storage** | 5GB standard (within free tier) | $0 |
| **Egress Traffic** | <1GB/month (within free tier) | $0 |
| **External IP** | Static IP address | $3-7 |
| **Monitoring** | Basic metrics (free tier) | $0 |

**TOTAL: ~$28-32/month**

### Free Tier Details
GCP provides generous free tier:
- **Compute Engine**: 1 x e2-micro (0.25-2 vCPU, 1GB RAM) - FREE but too small for our needs
- **Cloud Storage**: 5GB standard storage - FREE
- **Networking**: 1GB egress per month - FREE
- **Monitoring**: Free basic metrics

### Further Cost Reduction Options

1. **Use Preemptible VM**: Reduces compute cost by 80%
   - Cost: ~$5/month instead of $25
   - Caveat: VM can be terminated at any time (max 24h runtime)
   - Good for: Development/testing

2. **Use e2-small instead of e2-medium**: $12/month
   - Caveat: May be slower, less memory

3. **Stop VM when not in use**: Pay only for hours used
   - Stop at night: ~50% savings
   - Stop on weekends: ~30% additional savings

**With preemptible + scheduled stops: <$10/month!**

---

## DEPLOYMENT STEPS

### **Phase 1: Prerequisites**

#### Step 1.1: Install Tools

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL  # Restart shell

# Initialize gcloud
gcloud init
```

#### Step 1.2: Set Up GCP Project

```bash
# Create or select project
export PROJECT_ID="maxa-ds-toy"
gcloud projects create $PROJECT_ID --name="MAXA DS Toy"
gcloud config set project $PROJECT_ID

# Link billing account (required even for free tier)
# List billing accounts
gcloud billing accounts list

# Link to project
gcloud billing projects link $PROJECT_ID \
  --billing-account=YOUR_BILLING_ACCOUNT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com
gcloud services enable storage-api.googleapis.com
```

---

### **Phase 2: Create Compute VM**

#### Step 2.1: Create VM Instance

**Option A: Standard VM (~$25/month)**

```bash
# Create VM with docker pre-installed
gcloud compute instances create maxa-ds-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-balanced \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose git
    systemctl start docker
    systemctl enable docker
    usermod -aG docker $USER
  '
```

**Option B: Preemptible VM (~$5/month, better for learning)**

```bash
# Same as above but add --preemptible flag
gcloud compute instances create maxa-ds-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --preemptible \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-balanced \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose git
    systemctl start docker
    systemctl enable docker
    usermod -aG docker $USER
  '
```

**Option C: Spot VM (Even Cheaper, Lowest Cost)**

```bash
# Use spot instance for maximum savings
gcloud compute instances create maxa-ds-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --provisioning-model=SPOT \
  --instance-termination-action=STOP \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-standard \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose git curl
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
  '
```

#### Step 2.2: Configure Firewall

```bash
# Allow HTTP traffic (port 8001 for MCP server)
gcloud compute firewall-rules create allow-mcp-server \
  --allow=tcp:8001 \
  --target-tags=http-server \
  --description="Allow MCP server traffic"

# Allow MLflow (port 5000)
gcloud compute firewall-rules create allow-mlflow \
  --allow=tcp:5000 \
  --target-tags=http-server \
  --description="Allow MLflow UI"

# Allow Flower (port 5555)
gcloud compute firewall-rules create allow-flower \
  --allow=tcp:5555 \
  --target-tags=http-server \
  --description="Allow Flower UI"

# Allow SSH (should be default, but just in case)
gcloud compute firewall-rules create allow-ssh \
  --allow=tcp:22 \
  --description="Allow SSH"
```

#### Step 2.3: Reserve Static IP (Optional)

```bash
# Reserve static external IP
gcloud compute addresses create maxa-ds-ip --region=us-central1

# Get the IP address
gcloud compute addresses describe maxa-ds-ip --region=us-central1 --format='get(address)'

# Assign to VM
gcloud compute instances delete-access-config maxa-ds-vm --zone=us-central1-a
gcloud compute instances add-access-config maxa-ds-vm \
  --zone=us-central1-a \
  --address=$(gcloud compute addresses describe maxa-ds-ip --region=us-central1 --format='get(address)')
```

---

### **Phase 3: Set Up Cloud Storage**

```bash
# Create bucket for artifacts (free tier: 5GB)
gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$PROJECT_ID-artifacts

# Make bucket accessible
gsutil iam ch allAuthenticatedUsers:objectViewer gs://$PROJECT_ID-artifacts

# Or for private access only (recommended):
# Use VM service account
VM_SA=$(gcloud compute instances describe maxa-ds-vm --zone=us-central1-a --format='get(serviceAccounts[0].email)')
gsutil iam ch serviceAccount:$VM_SA:objectAdmin gs://$PROJECT_ID-artifacts
```

---

### **Phase 4: Deploy Application**

#### Step 4.1: SSH into VM

```bash
# SSH into the VM
gcloud compute ssh maxa-ds-vm --zone=us-central1-a

# Verify Docker is installed
docker --version
docker-compose --version
```

#### Step 4.2: Clone Repository and Set Up

```bash
# On the VM
cd ~
git clone https://github.com/yourusername/maxa-ds-agent.git
cd maxa-ds-agent

# Or upload your code via scp
# From local machine:
# gcloud compute scp --recurse /Users/emdim/dev/maxa-ds-agent maxa-ds-vm:~ --zone=us-central1-a
```

#### Step 4.3: Create Environment File

```bash
# Create .env file for docker-compose
cat > docker/.env <<EOF
# MongoDB
MONGO_USER=admin
MONGO_PASSWORD=changeme123
MONGO_DB=maxa_ds
MONGO_PORT=27017

# PostgreSQL (MLflow backend)
PG_USER=postgres
PG_PASSWORD=postgres123
PG_DATABASE=mlflow
PG_PORT=5432

# MinIO (we'll use GCS instead, but keep for compatibility)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# MLflow
MLFLOW_PORT=5000
MLFLOW_BUCKET_NAME=mlflow

# MCP Server
MCP_HOST=0.0.0.0
MCP_PORT=8001

# Redis
REDIS_PORT=6379

# Flower
FLOWER_PORT=5555

# GCS Configuration (instead of MinIO)
GCS_BUCKET=$PROJECT_ID-artifacts
GCS_PROJECT=$PROJECT_ID
EOF
```

#### Step 4.4: Modify Docker Compose for Toy Deployment

Create a simplified `docker/docker-compose-toy.yaml`:

```yaml
services:
  # Redis - in-memory cache and Celery broker
  redis:
    image: redis:alpine
    container_name: redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # PostgreSQL - MLflow backend store
  postgres:
    image: postgres:15-alpine
    container_name: postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${PG_USER}
      POSTGRES_PASSWORD: ${PG_PASSWORD}
      POSTGRES_DB: ${PG_DATABASE}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  # MongoDB - Document store for tool responses
  mongodb:
    image: mongo:7
    container_name: mongodb
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
      MONGO_INITDB_DATABASE: ${MONGO_DB}
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped

  # MinIO - Local object storage (lightweight alternative to GCS for toy setup)
  minio:
    image: minio/minio
    container_name: minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    command: server /data --address ":9000" --console-address ":9001"
    restart: unless-stopped

  # MLflow Server - Experiment tracking
  mlflow:
    build:
      context: ..
      dockerfile: docker/Dockerfile.mlflow
    container_name: mlflow
    ports:
      - "5000:5000"
    environment:
      - AWS_ACCESS_KEY_ID=${MINIO_ROOT_USER}
      - AWS_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}
      - MLFLOW_S3_ENDPOINT_URL=http://minio:9000
      - MLFLOW_S3_IGNORE_TLS=true
    command: >
      mlflow server
      --backend-store-uri postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DATABASE}
      --host 0.0.0.0
      --serve-artifacts
      --artifacts-destination s3://mlflow
    depends_on:
      - postgres
      - minio
    restart: unless-stopped

  # MCP Server - Main API
  mcp-server:
    build:
      context: ..
      dockerfile: docker/Dockerfile.mcp
    container_name: mcp-server
    ports:
      - "8001:8001"
    environment:
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8001
      - MONGO_USER=${MONGO_USER}
      - MONGO_PASSWORD=${MONGO_PASSWORD}
      - MONGO_HOST=mongodb
      - MONGO_PORT=27017
      - MONGO_DB=${MONGO_DB}
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
      - MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
      - REDIS_URL=redis://redis:6379/0
      - MLFLOW_SERVER_URL=http://mlflow:5000
    volumes:
      - ../datasets:/app/datasets
    depends_on:
      - redis
      - mongodb
      - minio
      - mlflow
    restart: unless-stopped

  # Celery Worker - Async job processing (only 1 worker for toy system)
  celery-worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.mcp
    container_name: celery-worker
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MONGO_USER=${MONGO_USER}
      - MONGO_PASSWORD=${MONGO_PASSWORD}
      - MONGO_HOST=mongodb
      - MONGO_PORT=27017
      - MONGO_DB=${MONGO_DB}
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
      - MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
      - MLFLOW_SERVER_URL=http://mlflow:5000
    command: ["celery", "-A", "src.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
    depends_on:
      - redis
      - mongodb
      - minio
    restart: unless-stopped

  # Flower - Celery monitoring UI
  flower:
    build:
      context: ..
      dockerfile: docker/Dockerfile.mcp
    container_name: flower
    ports:
      - "5555:5555"
    environment:
      - REDIS_URL=redis://redis:6379/0
    command: ["celery", "-A", "src.workers.celery_app", "flower", "--port=5555"]
    depends_on:
      - redis
      - celery-worker
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
  mongodb_data:
  minio_data:
```

#### Step 4.5: Build and Start Services

```bash
# On the VM, in the project directory
cd ~/maxa-ds-agent/docker

# Build images (this may take 5-10 minutes)
docker-compose -f docker-compose-toy.yaml build

# Start all services
docker-compose -f docker-compose-toy.yaml up -d

# Check status
docker-compose -f docker-compose-toy.yaml ps

# View logs
docker-compose -f docker-compose-toy.yaml logs -f

# Check individual service logs
docker logs mcp-server
docker logs celery-worker
docker logs mlflow
```

#### Step 4.6: Verify Deployment

```bash
# Get VM external IP
VM_IP=$(gcloud compute instances describe maxa-ds-vm --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "MCP Server: http://$VM_IP:8001"
echo "MLflow UI: http://$VM_IP:5000"
echo "Flower UI: http://$VM_IP:5555"
echo "MinIO Console: http://$VM_IP:9001"

# Test MCP server health
curl http://$VM_IP:8001/health

# Test MLflow
curl http://$VM_IP:5000/health
```

---

### **Phase 5: Configure Cursor to Use Toy System**

Update your Cursor MCP configuration (`~/.cursor/mcp.json` or workspace settings):

```json
{
  "mcpServers": {
    "maxa-data-scientist-toy": {
      "type": "http",
      "url": "http://YOUR_VM_IP:8001"
    }
  }
}
```

Replace `YOUR_VM_IP` with the actual IP address from the previous step.

---

### **Phase 6: Basic Monitoring (Optional)**

#### Step 6.1: Set Up Simple Monitoring Script

```bash
# On the VM
cat > ~/monitor.sh <<'EOF'
#!/bin/bash
echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=== Disk Usage ==="
df -h /

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== CPU Usage ==="
top -bn1 | head -20

echo -e "\n=== Recent Errors ==="
docker logs mcp-server --tail 10 2>&1 | grep -i error || echo "No recent errors"
EOF

chmod +x ~/monitor.sh

# Run monitoring
~/monitor.sh
```

#### Step 6.2: Set Up Auto-Restart (Optional)

```bash
# Create systemd service for auto-restart
sudo tee /etc/systemd/system/maxa-ds.service > /dev/null <<EOF
[Unit]
Description=MAXA DS Agent
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/$USER/maxa-ds-agent/docker
ExecStart=/usr/bin/docker-compose -f docker-compose-toy.yaml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose-toy.yaml down
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable maxa-ds.service
sudo systemctl start maxa-ds.service

# Check status
sudo systemctl status maxa-ds.service
```

---

### **Phase 7: Backup & Maintenance**

#### Step 7.1: Manual Backup Script

```bash
# Create backup script
cat > ~/backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

echo "Backing up data..."

# Backup MongoDB
docker exec mongodb mongodump --out=/data/backup --archive=/data/backup-$DATE.archive
docker cp mongodb:/data/backup-$DATE.archive $BACKUP_DIR/mongodb-$DATE.archive

# Backup PostgreSQL
docker exec postgres pg_dump -U postgres mlflow > $BACKUP_DIR/postgres-$DATE.sql

# Backup MinIO data
docker cp minio:/data $BACKUP_DIR/minio-$DATE

# Compress
tar -czf $BACKUP_DIR/backup-$DATE.tar.gz $BACKUP_DIR/*-$DATE.*

# Keep only last 7 backups
ls -t $BACKUP_DIR/backup-*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: $BACKUP_DIR/backup-$DATE.tar.gz"
EOF

chmod +x ~/backup.sh

# Run backup
~/backup.sh

# Schedule weekly backups (every Sunday at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * 0 ~/backup.sh") | crontab -
```

#### Step 7.2: Update Application

```bash
# Pull latest code
cd ~/maxa-ds-agent
git pull

# Rebuild and restart
cd docker
docker-compose -f docker-compose-toy.yaml build
docker-compose -f docker-compose-toy.yaml up -d

# Check logs for errors
docker-compose -f docker-compose-toy.yaml logs -f
```

---

## COST OPTIMIZATION TIPS

### 1. Stop VM When Not in Use

```bash
# Stop VM (from local machine)
gcloud compute instances stop maxa-ds-vm --zone=us-central1-a

# Start VM
gcloud compute instances start maxa-ds-vm --zone=us-central1-a
```

**Savings**: ~50% if stopped overnight, ~70% if stopped on weekends

### 2. Scheduled Start/Stop

```bash
# Create Cloud Scheduler jobs for auto start/stop

# Stop VM at 6 PM on weekdays
gcloud scheduler jobs create http stop-vm-weekday \
  --schedule="0 18 * * 1-5" \
  --uri="https://compute.googleapis.com/compute/v1/projects/$PROJECT_ID/zones/us-central1-a/instances/maxa-ds-vm/stop" \
  --http-method=POST \
  --oauth-service-account-email=YOUR_SERVICE_ACCOUNT

# Start VM at 8 AM on weekdays
gcloud scheduler jobs create http start-vm-weekday \
  --schedule="0 8 * * 1-5" \
  --uri="https://compute.googleapis.com/compute/v1/projects/$PROJECT_ID/zones/us-central1-a/instances/maxa-ds-vm/start" \
  --http-method=POST \
  --oauth-service-account-email=YOUR_SERVICE_ACCOUNT
```

### 3. Use Smaller Machine Type

If performance is acceptable, downgrade:

```bash
# Stop VM
gcloud compute instances stop maxa-ds-vm --zone=us-central1-a

# Change machine type
gcloud compute instances set-machine-type maxa-ds-vm \
  --zone=us-central1-a \
  --machine-type=e2-small

# Start VM
gcloud compute instances start maxa-ds-vm --zone=us-central1-a
```

**e2-small cost**: ~$12/month (50% savings)

### 4. Set Budget Alerts

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="MAXA DS Toy Budget" \
  --budget-amount=50 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## TESTING & USAGE

### Test MCP Server

```bash
# From your local machine with Cursor configured

# List available datasets (example tool call)
# Cursor will call: http://YOUR_VM_IP:8001/tools/list_available_datasets

# Or test directly with curl
curl -X POST http://YOUR_VM_IP:8001/tools/list_available_datasets \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Access Web UIs

1. **MLflow UI**: `http://YOUR_VM_IP:5000`
   - View experiments
   - Track model metrics
   - Browse artifacts

2. **Flower UI**: `http://YOUR_VM_IP:5555`
   - Monitor Celery tasks
   - View worker status
   - Track job queues

3. **MinIO Console**: `http://YOUR_VM_IP:9001`
   - Browse object storage
   - View buckets and files
   - Login: minioadmin / minioadmin123

---

## TROUBLESHOOTING

### Container Won't Start

```bash
# Check logs
docker logs mcp-server
docker logs celery-worker

# Check resource usage
docker stats

# Restart specific service
docker-compose -f docker-compose-toy.yaml restart mcp-server
```

### Out of Memory

```bash
# Check memory usage
free -h

# Stop some services temporarily
docker stop flower  # Flower is optional for basic operation

# Or upgrade to e2-standard-2 (2 vCPU, 8GB RAM) - $48/month
gcloud compute instances stop maxa-ds-vm --zone=us-central1-a
gcloud compute instances set-machine-type maxa-ds-vm \
  --zone=us-central1-a \
  --machine-type=e2-standard-2
gcloud compute instances start maxa-ds-vm --zone=us-central1-a
```

### Can't Connect from Cursor

```bash
# Check firewall rules
gcloud compute firewall-rules list

# Check if MCP server is running
docker ps | grep mcp-server

# Check if port is open
curl http://YOUR_VM_IP:8001/health

# Check VM external IP hasn't changed (for non-static IPs)
gcloud compute instances describe maxa-ds-vm --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### VM Keeps Getting Terminated (Preemptible/Spot)

This is expected behavior for preemptible/spot VMs:

```bash
# Check if VM is still running
gcloud compute instances describe maxa-ds-vm --zone=us-central1-a

# Restart if needed
gcloud compute instances start maxa-ds-vm --zone=us-central1-a

# Services will auto-start if you configured systemd service
```

---

## CLEANUP (Tear Down)

When you're done learning and want to delete everything:

```bash
# Stop and remove all containers
cd ~/maxa-ds-agent/docker
docker-compose -f docker-compose-toy.yaml down -v

# Delete VM
gcloud compute instances delete maxa-ds-vm --zone=us-central1-a

# Delete static IP (if created)
gcloud compute addresses delete maxa-ds-ip --region=us-central1

# Delete firewall rules
gcloud compute firewall-rules delete allow-mcp-server
gcloud compute firewall-rules delete allow-mlflow
gcloud compute firewall-rules delete allow-flower

# Delete storage bucket
gsutil -m rm -r gs://$PROJECT_ID-artifacts

# Delete project (optional - removes everything)
gcloud projects delete $PROJECT_ID
```

---

## LEARNING EXERCISES

### Exercise 1: Understanding Docker Compose
```bash
# View running containers
docker ps

# Check resource usage
docker stats

# View logs of specific service
docker logs -f mcp-server

# Execute command inside container
docker exec -it mcp-server /bin/bash

# Inspect container
docker inspect mcp-server
```

### Exercise 2: Database Exploration
```bash
# Connect to MongoDB
docker exec -it mongodb mongosh -u admin -p changeme123

# Show databases
show dbs

# Use maxa_ds database
use maxa_ds

# List collections
show collections

# Query tool responses
db.tool_responses.find().limit(5)
```

### Exercise 3: Scaling Workers
```bash
# Scale Celery workers
docker-compose -f docker-compose-toy.yaml up -d --scale celery-worker=3

# View in Flower UI
# Open http://YOUR_VM_IP:5555
```

### Exercise 4: Cost Monitoring
```bash
# Check current month costs
gcloud billing accounts list
# Visit: https://console.cloud.google.com/billing

# Set up budget alerts (see Cost Optimization section)
```

---

## COMPARISON: Toy vs Production

| Feature | Toy System | Production System |
|---------|-----------|-------------------|
| **Cost** | $20-50/month | $800-2,500/month |
| **Architecture** | Single VM + Docker Compose | GKE cluster + managed services |
| **Scalability** | 1-5 users | 50-100+ concurrent users |
| **Availability** | Best effort (~95%) | 99.5% SLA |
| **Redundancy** | None | Multiple replicas |
| **Monitoring** | Basic logs | Full observability stack |
| **Backups** | Manual | Automated daily |
| **Deployment** | Manual SSH | CI/CD pipeline |
| **Security** | Basic firewall | VPC, encryption, IAM |
| **Maintenance** | Manual updates | Automated rolling updates |

---

## NEXT STEPS

After successfully deploying the toy system:

1. **Experiment**: Try different MCP tools via Cursor
2. **Monitor**: Watch Flower and MLflow UIs during usage
3. **Learn**: Explore Docker Compose, understand each service
4. **Optimize**: Try different VM sizes, measure performance
5. **Backup**: Practice backup and restore procedures
6. **Scale Up**: When ready, migrate to production architecture

---

## USEFUL RESOURCES

- [GCP Free Tier](https://cloud.google.com/free)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [GCP Compute Engine Pricing](https://cloud.google.com/compute/pricing)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Celery Documentation](https://docs.celeryq.dev/)

---

**End of Toy Deployment Guide**

**Happy Learning! 🚀**
