# GCP Deployment Guide - Production System

## Table of Contents
1. [Non-Functional Requirements](#non-functional-requirements)
2. [Architecture Overview](#architecture-overview)
3. [Deployment Steps](#deployment-steps)
4. [Cost Estimation](#cost-estimation)

---

## NON-FUNCTIONAL REQUIREMENTS (System Design Perspective)

### 1. **Scalability Requirements**

**Horizontal Scalability:**
- **MCP Server**: Must support 50-100+ concurrent AI agents making tool calls
- **Celery Workers**: Auto-scale based on queue depth (5-50 workers)
- **Database**: Handle 1000+ tool executions per hour, 10TB+ artifact storage
- **Peak Load**: 500 tool calls/minute during batch training operations

**Vertical Scalability:**
- ML training jobs require 8-32 CPU cores, 32-128GB RAM
- Data processing for large datasets (>1GB CSVs)

### 2. **Performance Requirements**

**Latency:**
- Tool call response (P95): <2 seconds for lightweight ops
- Job submission: <500ms
- Dataset loading: <30s for 100MB files
- Model inference: <1s for batch predictions
- Storage read/write: <200ms (P95)

**Throughput:**
- 100+ concurrent async jobs
- 1000+ database operations per second
- 500MB/s artifact I/O to object storage

### 3. **Reliability & Availability**

**Uptime:**
- **Target SLA**: 99.5% (3.65 hours/month downtime)
- **RTO** (Recovery Time Objective): <1 hour
- **RPO** (Recovery Point Objective): <24 hours

**Fault Tolerance:**
- Zero-downtime deployments (rolling updates)
- Automatic worker recovery on failure
- Database replication for disaster recovery
- Circuit breakers for external dependencies (Snowflake)

### 4. **Durability & Data Integrity**

- **Experiment artifacts**: Multi-region replication
- **Database backups**: Daily automated backups with 30-day retention
- **Transactional integrity**: ACID for metadata, eventual consistency for large artifacts
- **Data lineage**: Full traceability from raw data → features → models

### 5. **Security Requirements**

**Authentication & Authorization:**
- OAuth 2.0 / Service accounts for API access
- IAM roles for GCP resource access
- Secrets management (GCP Secret Manager)

**Network Security:**
- VPC with private subnets for databases
- Cloud NAT for outbound traffic
- Load balancer with SSL/TLS termination
- Firewall rules (least privilege)

**Data Security:**
- Encryption at rest (GCS, Cloud SQL, MongoDB Atlas)
- Encryption in transit (TLS 1.3)
- Audit logging for all data access
- PII detection and masking

### 6. **Observability**

**Monitoring:**
- Application metrics (Prometheus + Cloud Monitoring)
- Infrastructure metrics (CPU, memory, disk, network)
- Custom ML metrics (training time, dataset size, model performance)

**Logging:**
- Centralized logging (Cloud Logging)
- Structured JSON logs with correlation IDs
- Log retention: 30 days

**Tracing:**
- Distributed tracing (OpenTelemetry → Cloud Trace)
- Request/response tracking across services

**Alerting:**
- Latency degradation (P95 > 5s)
- Error rate spikes (>1%)
- Resource saturation (CPU > 80%, Memory > 85%)
- Failed job rate (>5%)

### 7. **Cost Optimization**

- Use preemptible VMs for Celery workers (up to 80% cost savings)
- Auto-scaling to match workload
- Lifecycle policies for object storage (archive after 90 days)
- Right-sizing based on actual usage patterns

### 8. **Maintainability**

- Infrastructure as Code (Terraform)
- GitOps deployment workflow
- Automated testing (unit, integration, e2e)
- Rolling updates with health checks
- Feature flags for gradual rollouts

---

## ARCHITECTURE OVERVIEW

```
┌──────────────────────────────────────────────────────────────────┐
│                        Internet/AI Agents                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Cloud Load       │
                    │  Balancer (HTTPS) │
                    └────────┬─────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                      VPC (Private Network)                        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Compute Resources (GKE or GCE)                 │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │  MCP Server  │  │    Celery    │  │    Flower    │    │ │
│  │  │  (3 pods)    │  │  Workers     │  │  (Monitoring)│    │ │
│  │  │              │  │  (Auto-scale)│  │              │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  │                                                             │ │
│  │  ┌──────────────┐                                          │ │
│  │  │  MLflow      │                                          │ │
│  │  │  Server      │                                          │ │
│  │  └──────────────┘                                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Managed Services                           │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │  Memorystore │  │   Cloud SQL  │  │   MongoDB    │    │ │
│  │  │  (Redis)     │  │ (PostgreSQL) │  │   Atlas      │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Cloud Storage   │
                    │  (GCS - Artifacts)│
                    └──────────────────┘
```

**Key Components:**
- **GKE Cluster**: Kubernetes cluster with 3+ nodes, auto-scaling enabled
- **MCP Server**: 3 replicas for high availability
- **Celery Workers**: Auto-scaling 5-50 workers based on queue depth
- **MLflow Server**: 2 replicas for experiment tracking
- **Cloud SQL**: PostgreSQL for MLflow backend store
- **Memorystore**: Redis for Celery broker and caching
- **MongoDB Atlas**: Document store for tool responses and notes
- **Cloud Storage**: Object storage for large artifacts
- **Cloud Load Balancer**: HTTPS ingress with SSL termination

---

## DEPLOYMENT STEPS

### **Phase 1: Prerequisites & Initial Setup**

#### Step 1.1: Install Required Tools

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
gcloud init

# Install kubectl
gcloud components install kubectl

# Install Terraform
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads

# Install Helm (for Kubernetes deployments)
brew install helm
```

#### Step 1.2: Configure GCP Project

```bash
# Set project
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export ZONE="us-central1-a"

gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE

# Enable required APIs
gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  sql-component.googleapis.com \
  redis.googleapis.com \
  storage-api.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

#### Step 1.3: Create Service Account

```bash
# Create service account for the application
gcloud iam service-accounts create maxa-ds-agent \
  --display-name="MAXA DS Agent"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/monitoring.metricWriter"
```

---

### **Phase 2: Set Up Managed Services**

#### Step 2.1: Create VPC Network

```bash
# Create VPC
gcloud compute networks create maxa-vpc \
  --subnet-mode=custom \
  --bgp-routing-mode=regional

# Create subnet
gcloud compute networks subnets create maxa-subnet \
  --network=maxa-vpc \
  --region=$REGION \
  --range=10.0.0.0/24 \
  --enable-private-ip-google-access

# Create firewall rules
gcloud compute firewall-rules create allow-internal \
  --network=maxa-vpc \
  --allow=tcp,udp,icmp \
  --source-ranges=10.0.0.0/24

gcloud compute firewall-rules create allow-health-checks \
  --network=maxa-vpc \
  --allow=tcp \
  --source-ranges=35.191.0.0/16,130.211.0.0/22
```

#### Step 2.2: Set Up Cloud Storage (Replaces MinIO)

```bash
# Create bucket for MLflow artifacts
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$PROJECT_ID-mlflow-artifacts

# Create bucket for general storage
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$PROJECT_ID-maxa-storage

# Enable versioning
gsutil versioning set on gs://$PROJECT_ID-mlflow-artifacts
gsutil versioning set on gs://$PROJECT_ID-maxa-storage

# Set lifecycle policy (archive after 90 days, delete after 1 year)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365}
      }
    ]
  }
}
EOF
gsutil lifecycle set lifecycle.json gs://$PROJECT_ID-mlflow-artifacts

# Set IAM permissions
gsutil iam ch serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin \
  gs://$PROJECT_ID-mlflow-artifacts
gsutil iam ch serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin \
  gs://$PROJECT_ID-maxa-storage
```

#### Step 2.3: Set Up Cloud SQL (PostgreSQL for MLflow)

```bash
# Generate random password
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Create Cloud SQL PostgreSQL instance
gcloud sql instances create mlflow-db \
  --database-version=POSTGRES_15 \
  --cpu=2 \
  --memory=8GB \
  --region=$REGION \
  --network=projects/$PROJECT_ID/global/networks/maxa-vpc \
  --no-assign-ip \
  --backup \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --retained-backups-count=7 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04

# Create database
gcloud sql databases create mlflow \
  --instance=mlflow-db

# Create user
gcloud sql users create mlflow_user \
  --instance=mlflow-db \
  --password=$POSTGRES_PASSWORD

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe mlflow-db --format='get(connectionName)')
echo "Cloud SQL Connection Name: $CONNECTION_NAME"

# Store password in Secret Manager
echo -n "$POSTGRES_PASSWORD" | gcloud secrets create postgres-password --data-file=-
```

#### Step 2.4: Set Up Memorystore (Redis)

```bash
# Create Redis instance with high availability
gcloud redis instances create maxa-redis \
  --size=5 \
  --region=$REGION \
  --network=projects/$PROJECT_ID/global/networks/maxa-vpc \
  --redis-version=redis_6_x \
  --tier=standard \
  --replica-count=1 \
  --enable-auth

# Get Redis host and auth string
REDIS_HOST=$(gcloud redis instances describe maxa-redis --region=$REGION --format='get(host)')
REDIS_AUTH=$(gcloud redis instances describe maxa-redis --region=$REGION --format='get(authString)')

echo "Redis Host: $REDIS_HOST"
echo "Redis Auth: $REDIS_AUTH"
```

#### Step 2.5: Set Up MongoDB Atlas

**Manual Setup Required:**

1. Go to https://cloud.mongodb.com/
2. Create a new organization/project
3. Create cluster:
   - **Cloud Provider**: Google Cloud Platform
   - **Region**: Same as your GCP region (us-central1)
   - **Cluster Tier**: M10 (Production)
   - **Cluster Name**: maxa-ds-cluster
4. Configure Network Access:
   - Go to "Network Access"
   - Add VPC Peering to your GCP VPC
   - Peering Connection: `projects/$PROJECT_ID/global/networks/maxa-vpc`
5. Create Database User:
   - Username: `maxa_admin`
   - Password: Generate strong password
   - Database: `maxa_ds`
   - Role: `readWrite`
6. Get connection string:
   - Format: `mongodb+srv://maxa_admin:PASSWORD@cluster.mongodb.net/maxa_ds?retryWrites=true&w=majority`

**Alternative: Self-Hosted MongoDB on GCE**

```bash
# Create VM for MongoDB
gcloud compute instances create mongodb-server \
  --machine-type=n1-standard-4 \
  --subnet=maxa-subnet \
  --no-address \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=200GB \
  --boot-disk-type=pd-ssd \
  --tags=mongodb

# Create firewall rule for MongoDB
gcloud compute firewall-rules create allow-mongodb \
  --network=maxa-vpc \
  --allow=tcp:27017 \
  --source-ranges=10.0.0.0/24 \
  --target-tags=mongodb

# SSH and install MongoDB (manual setup required)
# Follow: https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
```

#### Step 2.6: Set Up Secrets Manager

```bash
# Store MongoDB credentials
MONGODB_URI="mongodb://user:password@host:27017/maxa_ds?authSource=admin"
echo -n "$MONGODB_URI" | gcloud secrets create mongodb-uri --data-file=-

# Store Redis URL with auth
echo -n "redis://:${REDIS_AUTH}@${REDIS_HOST}:6379/0" | gcloud secrets create redis-url --data-file=-

# Store GCS credentials for S3-compatible access
echo -n "your-access-key" | gcloud secrets create gcs-access-key --data-file=-
echo -n "your-secret-key" | gcloud secrets create gcs-secret-key --data-file=-

# Grant Secret Manager access to service account
gcloud secrets add-iam-policy-binding mongodb-uri \
  --member="serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding redis-url \
  --member="serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding postgres-password \
  --member="serviceAccount:maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

### **Phase 3: Container Registry & Build**

#### Step 3.1: Build and Push Docker Images

```bash
# Enable Artifact Registry
gcloud services enable artifactregistry.googleapis.com

# Create repository
gcloud artifacts repositories create maxa-ds-agent \
  --repository-format=docker \
  --location=$REGION \
  --description="MAXA DS Agent container images"

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Navigate to project root
cd /Users/emdim/dev/maxa-ds-agent

# Build and push MCP server image
docker build -f docker/Dockerfile.mcp \
  -t ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mcp-server:latest \
  -t ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mcp-server:$(git rev-parse --short HEAD) \
  .

docker push ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mcp-server:latest
docker push ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mcp-server:$(git rev-parse --short HEAD)

# Build and push MLflow server image
docker build -f docker/Dockerfile.mlflow \
  -t ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mlflow-server:latest \
  -t ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mlflow-server:$(git rev-parse --short HEAD) \
  .

docker push ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mlflow-server:latest
docker push ${REGION}-docker.pkg.dev/$PROJECT_ID/maxa-ds-agent/mlflow-server:$(git rev-parse --short HEAD)
```

---

### **Phase 4: Kubernetes Deployment (GKE)**

#### Step 4.1: Create GKE Cluster

```bash
# Create GKE cluster with autoscaling
gcloud container clusters create maxa-ds-cluster \
  --region=$REGION \
  --num-nodes=2 \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10 \
  --machine-type=n1-standard-4 \
  --disk-size=100GB \
  --disk-type=pd-standard \
  --enable-autorepair \
  --enable-autoupgrade \
  --network=maxa-vpc \
  --subnetwork=maxa-subnet \
  --enable-stackdriver-kubernetes \
  --enable-ip-alias \
  --workload-pool=$PROJECT_ID.svc.id.goog \
  --addons=HttpLoadBalancing,HorizontalPodAutoscaling \
  --maintenance-window-start=2024-01-01T03:00:00Z \
  --maintenance-window-duration=4h \
  --enable-shielded-nodes

# Get credentials
gcloud container clusters get-credentials maxa-ds-cluster --region=$REGION
```

#### Step 4.2: Configure Workload Identity

```bash
# Create Kubernetes service account
kubectl create namespace maxa-ds
kubectl create serviceaccount maxa-ds-sa -n maxa-ds

# Bind GCP service account to Kubernetes service account
gcloud iam service-accounts add-iam-policy-binding \
  maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:$PROJECT_ID.svc.id.goog[maxa-ds/maxa-ds-sa]"

# Annotate Kubernetes service account
kubectl annotate serviceaccount maxa-ds-sa \
  -n maxa-ds \
  iam.gke.io/gcp-service-account=maxa-ds-agent@$PROJECT_ID.iam.gserviceaccount.com
```

#### Step 4.3: Create Kubernetes Secrets

```bash
# Create secrets from Secret Manager
kubectl create secret generic app-secrets -n maxa-ds \
  --from-literal=mongodb-uri="$(gcloud secrets versions access latest --secret=mongodb-uri)" \
  --from-literal=redis-url="$(gcloud secrets versions access latest --secret=redis-url)" \
  --from-literal=postgres-password="$(gcloud secrets versions access latest --secret=postgres-password)" \
  --from-literal=gcs-access-key="$(gcloud secrets versions access latest --secret=gcs-access-key)" \
  --from-literal=gcs-secret-key="$(gcloud secrets versions access latest --secret=gcs-secret-key)"
```

#### Step 4.4: Create Kubernetes Manifests

Create `k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: maxa-config
  namespace: maxa-ds
data:
  MONGO_DB: "maxa_ds"
  MONGO_PORT: "27017"
  MLFLOW_BUCKET_NAME: "mlflow-artifacts"
  GCS_ENDPOINT: "storage.googleapis.com"
  MCP_HOST: "0.0.0.0"
  MCP_PORT: "8001"
  MLFLOW_PORT: "5000"
```

Create `k8s/deployment.yaml`:

```yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: maxa-ds
  labels:
    app: mcp-server
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8001"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: maxa-ds-sa
      containers:
      - name: mcp-server
        image: us-central1-docker.pkg.dev/PROJECT_ID/maxa-ds-agent/mcp-server:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8001
          name: http
        env:
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: mongodb-uri
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        - name: MLFLOW_SERVER_URL
          value: "http://mlflow-server:5000"
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: "/var/secrets/google/key.json"
        envFrom:
        - configMapRef:
            name: maxa-config
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: maxa-ds
  labels:
    app: celery-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      serviceAccountName: maxa-ds-sa
      containers:
      - name: worker
        image: us-central1-docker.pkg.dev/PROJECT_ID/maxa-ds-agent/mcp-server:latest
        imagePullPolicy: Always
        command: ["celery", "-A", "src.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
        env:
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: mongodb-uri
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        - name: MLFLOW_SERVER_URL
          value: "http://mlflow-server:5000"
        envFrom:
        - configMapRef:
            name: maxa-config
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "16Gi"
            cpu: "8000m"
        livenessProbe:
          exec:
            command:
            - celery
            - -A
            - src.workers.celery_app
            - inspect
            - ping
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 10

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-server
  namespace: maxa-ds
  labels:
    app: mlflow-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mlflow-server
  template:
    metadata:
      labels:
        app: mlflow-server
    spec:
      serviceAccountName: maxa-ds-sa
      containers:
      - name: mlflow
        image: us-central1-docker.pkg.dev/PROJECT_ID/maxa-ds-agent/mlflow-server:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 5000
          name: http
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: postgres-password
        - name: MLFLOW_BACKEND_STORE_URI
          value: "postgresql://mlflow_user:$(POSTGRES_PASSWORD)@CLOUDSQL_IP:5432/mlflow"
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: "/var/secrets/google/key.json"
        - name: GCS_BUCKET
          value: "PROJECT_ID-mlflow-artifacts"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flower
  namespace: maxa-ds
  labels:
    app: flower
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flower
  template:
    metadata:
      labels:
        app: flower
    spec:
      containers:
      - name: flower
        image: us-central1-docker.pkg.dev/PROJECT_ID/maxa-ds-agent/mcp-server:latest
        imagePullPolicy: Always
        command: ["celery", "-A", "src.workers.celery_app", "flower", "--port=5555"]
        ports:
        - containerPort: 5555
          name: http
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server
  namespace: maxa-ds
  labels:
    app: mcp-server
spec:
  type: ClusterIP
  ports:
  - port: 8001
    targetPort: 8001
    protocol: TCP
    name: http
  selector:
    app: mcp-server

---
apiVersion: v1
kind: Service
metadata:
  name: mlflow-server
  namespace: maxa-ds
  labels:
    app: mlflow-server
spec:
  type: ClusterIP
  ports:
  - port: 5000
    targetPort: 5000
    protocol: TCP
    name: http
  selector:
    app: mlflow-server

---
apiVersion: v1
kind: Service
metadata:
  name: flower
  namespace: maxa-ds
  labels:
    app: flower
spec:
  type: ClusterIP
  ports:
  - port: 5555
    targetPort: 5555
    protocol: TCP
    name: http
  selector:
    app: flower

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa
  namespace: maxa-ds
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
  namespace: maxa-ds
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Create `k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: maxa-ingress
  namespace: maxa-ds
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "maxa-ip"
    networking.gke.io/managed-certificates: "maxa-cert"
    kubernetes.io/ingress.allow-http: "false"
spec:
  rules:
  - host: maxa-ds.yourdomain.com
    http:
      paths:
      - path: /mcp
        pathType: Prefix
        backend:
          service:
            name: mcp-server
            port:
              number: 8001
      - path: /mlflow
        pathType: Prefix
        backend:
          service:
            name: mlflow-server
            port:
              number: 5000
      - path: /flower
        pathType: Prefix
        backend:
          service:
            name: flower
            port:
              number: 5555

---
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: maxa-cert
  namespace: maxa-ds
spec:
  domains:
    - maxa-ds.yourdomain.com
```

#### Step 4.5: Deploy to GKE

```bash
# Create namespace
kubectl create namespace maxa-ds

# Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get pods -n maxa-ds -w

# Check services
kubectl get services -n maxa-ds

# Check ingress (may take 10-15 minutes to provision)
kubectl get ingress -n maxa-ds

# View logs
kubectl logs -f deployment/mcp-server -n maxa-ds
kubectl logs -f deployment/celery-worker -n maxa-ds
```

#### Step 4.6: Create Preemptible Node Pool for Cost Savings

```bash
# Create preemptible node pool for Celery workers
gcloud container node-pools create worker-pool \
  --cluster=maxa-ds-cluster \
  --region=$REGION \
  --preemptible \
  --num-nodes=2 \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=20 \
  --machine-type=n1-highmem-4 \
  --disk-size=100GB \
  --disk-type=pd-standard

# Add node selector to worker deployment
kubectl patch deployment celery-worker -n maxa-ds \
  --type=json \
  -p='[{"op": "add", "path": "/spec/template/spec/nodeSelector", "value": {"cloud.google.com/gke-preemptible": "true"}}]'
```

---

### **Phase 5: Monitoring & Observability**

#### Step 5.1: Set Up Cloud Monitoring

```bash
# Create uptime check for MCP server
gcloud monitoring uptime create maxa-mcp-uptime \
  --resource-type=uptime-url \
  --host=maxa-ds.yourdomain.com \
  --path=/mcp/health \
  --check-interval=60s

# Create alert policy for high latency
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="MCP Server High Latency" \
  --condition-threshold-value=2.0 \
  --condition-threshold-duration=300s \
  --condition-display-name="P95 latency > 2s" \
  --aggregation-alignment-period=60s

# Create alert for error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-threshold-value=0.01 \
  --condition-threshold-duration=300s
```

#### Step 5.2: Set Up Cloud Logging

```bash
# Create log-based metrics
gcloud logging metrics create error_rate \
  --description="Rate of errors in MCP server" \
  --log-filter='resource.type="k8s_container" AND resource.labels.namespace_name="maxa-ds" AND jsonPayload.level="ERROR"'

gcloud logging metrics create tool_execution_count \
  --description="Count of tool executions" \
  --log-filter='resource.type="k8s_container" AND jsonPayload.event="tool_execution"'

# View logs
gcloud logging read \
  "resource.type=k8s_container AND resource.labels.namespace_name=maxa-ds" \
  --limit 50 \
  --format json

# Create log sink for long-term storage
gcloud logging sinks create maxa-logs-sink \
  gs://$PROJECT_ID-logs \
  --log-filter='resource.type="k8s_container" AND resource.labels.namespace_name="maxa-ds"'
```

#### Step 5.3: Set Up Cloud Trace

OpenTelemetry is already configured in the application. Traces will automatically appear in Cloud Trace.

```bash
# View traces
gcloud trace list --limit=10

# Navigate to Cloud Console > Trace
open "https://console.cloud.google.com/traces/list?project=$PROJECT_ID"
```

---

### **Phase 6: CI/CD Pipeline**

Create `.github/workflows/deploy-gcp-production.yml`:

```yaml
name: Deploy to GCP Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  PROJECT_ID: your-project-id
  REGION: us-central1
  GKE_CLUSTER: maxa-ds-cluster
  REGISTRY: us-central1-docker.pkg.dev

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      
      - name: Run tests
        run: pytest --cov=src tests/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Configure Docker
        run: gcloud auth configure-docker ${{ env.REGISTRY }}
      
      - name: Build MCP Server image
        run: |
          docker build -f docker/Dockerfile.mcp \
            -t ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mcp-server:${{ github.sha }} \
            -t ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mcp-server:latest \
            .
      
      - name: Build MLflow Server image
        run: |
          docker build -f docker/Dockerfile.mlflow \
            -t ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mlflow-server:${{ github.sha }} \
            -t ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mlflow-server:latest \
            .
      
      - name: Push images
        run: |
          docker push ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mcp-server:${{ github.sha }}
          docker push ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mcp-server:latest
          docker push ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mlflow-server:${{ github.sha }}
          docker push ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mlflow-server:latest
      
      - name: Get GKE credentials
        run: |
          gcloud container clusters get-credentials ${{ env.GKE_CLUSTER }} --region=${{ env.REGION }}
      
      - name: Deploy to GKE
        run: |
          kubectl set image deployment/mcp-server \
            mcp-server=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mcp-server:${{ github.sha }} \
            -n maxa-ds
          
          kubectl set image deployment/celery-worker \
            worker=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mcp-server:${{ github.sha }} \
            -n maxa-ds
          
          kubectl set image deployment/mlflow-server \
            mlflow=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/maxa-ds-agent/mlflow-server:${{ github.sha }} \
            -n maxa-ds
      
      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/mcp-server -n maxa-ds --timeout=10m
          kubectl rollout status deployment/celery-worker -n maxa-ds --timeout=10m
          kubectl rollout status deployment/mlflow-server -n maxa-ds --timeout=10m
      
      - name: Verify deployment
        run: |
          kubectl get pods -n maxa-ds
          kubectl get services -n maxa-ds
      
      - name: Run smoke tests
        run: |
          # Add smoke test commands here
          curl -f https://maxa-ds.yourdomain.com/mcp/health || exit 1
```

---

### **Phase 7: Disaster Recovery & Backups**

#### Step 7.1: Automated Backups

```bash
# Cloud SQL backups are already configured (daily at 3 AM)
# Verify backup configuration
gcloud sql instances describe mlflow-db --format='get(settings.backupConfiguration)'

# MongoDB Atlas: Configure automated backups in Atlas console
# - Continuous backups (point-in-time recovery)
# - Snapshot schedule: Daily at 2 AM
# - Retention: 30 days

# GCS: Versioning is already enabled
# Add backup bucket for critical data
gsutil mb -p $PROJECT_ID -c NEARLINE -l $REGION gs://$PROJECT_ID-backups

# Create backup script
cat > backup-gcs.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
gsutil -m rsync -r gs://$PROJECT_ID-maxa-storage gs://$PROJECT_ID-backups/maxa-storage-$DATE
EOF

chmod +x backup-gcs.sh
```

#### Step 7.2: Disaster Recovery Plan

Document in `docs/DR_PLAN.md`:

1. **Database Recovery**:
   - Cloud SQL: Restore from automated backup or point-in-time recovery
   - MongoDB Atlas: Restore from snapshot
   - RTO: 1 hour, RPO: 24 hours

2. **Object Storage Recovery**:
   - GCS: Restore from versioned objects or backup bucket
   - RTO: 30 minutes, RPO: 24 hours

3. **Application Recovery**:
   - GKE: Re-deploy from container images in Artifact Registry
   - RTO: 15 minutes, RPO: 0 (stateless)

---

## COST ESTIMATION

### Monthly Costs (US Central1 Region)

#### Compute (GKE)
- **Default Node Pool**: 2-10 x n1-standard-4 (4 vCPU, 15GB RAM)
  - Minimum (2 nodes): ~$150/month
  - Average (5 nodes): ~$375/month
  - Maximum (10 nodes): ~$750/month

- **Preemptible Worker Pool**: 2-20 x n1-highmem-4 (4 vCPU, 26GB RAM)
  - Minimum (2 nodes): ~$60/month
  - Average (10 nodes): ~$300/month
  - Maximum (20 nodes): ~$600/month

**Total Compute**: $210-$1,350/month (depends on load)

#### Managed Services
- **Cloud SQL PostgreSQL** (2 vCPU, 8GB RAM): ~$150/month
- **Memorystore Redis** (5GB Standard with replica): ~$180/month
- **MongoDB Atlas** (M10, 10GB storage): ~$60/month

**Total Managed Services**: $390/month

#### Storage
- **Cloud Storage** (500GB + operations): ~$20/month
- **Cloud SQL Storage** (100GB SSD): ~$17/month
- **Persistent Disks** (GKE nodes, 1TB total): ~$40/month

**Total Storage**: $77/month

#### Networking
- **Cloud Load Balancer**: ~$20/month
- **Egress Traffic** (100GB/month): ~$12/month
- **VPC**: Free

**Total Networking**: $32/month

#### Monitoring & Logging
- **Cloud Logging** (50GB/month): ~$25/month
- **Cloud Monitoring**: ~$10/month
- **Cloud Trace**: ~$5/month

**Total Observability**: $40/month

#### Miscellaneous
- **Container Registry** (storage + bandwidth): ~$10/month
- **Secret Manager** (10 secrets): ~$1/month

**Total Misc**: $11/month

---

### **TOTAL ESTIMATED MONTHLY COST**

| Scenario | Monthly Cost |
|----------|--------------|
| **Minimum** (low load, 2+2 nodes) | ~$760/month |
| **Average** (medium load, 5+10 nodes) | ~$1,385/month |
| **Maximum** (high load, 10+20 nodes) | ~$2,500/month |

**Cost Optimization Tips:**
1. Use preemptible VMs for 80% cost savings on workers
2. Enable cluster autoscaler to scale down during off-hours
3. Use committed use discounts for predictable workloads (30% savings)
4. Archive old data to Nearline/Coldline storage
5. Set budget alerts at $1,500/month threshold

---

## POST-DEPLOYMENT CHECKLIST

- [ ] All services are running (`kubectl get pods -n maxa-ds`)
- [ ] Health checks are passing
- [ ] MCP server is accessible via load balancer
- [ ] MLflow UI is accessible
- [ ] Flower (Celery monitoring) is accessible
- [ ] Database connections are working
- [ ] Cloud Storage buckets are accessible
- [ ] Logs are flowing to Cloud Logging
- [ ] Metrics are appearing in Cloud Monitoring
- [ ] Alerts are configured
- [ ] Backups are running
- [ ] CI/CD pipeline is working
- [ ] Documentation is updated
- [ ] Team has been trained on operations

---

## SUPPORT & TROUBLESHOOTING

### Common Issues

**1. Pods stuck in Pending state**
```bash
kubectl describe pod <pod-name> -n maxa-ds
# Check for resource constraints or node availability
```

**2. Connection to Cloud SQL fails**
```bash
# Verify Cloud SQL Proxy is working
gcloud sql instances describe mlflow-db --format='get(ipAddresses)'
```

**3. High costs**
```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n maxa-ds

# Review billing
gcloud billing accounts list
```

**4. Performance issues**
```bash
# Check HPA status
kubectl get hpa -n maxa-ds

# Check resource utilization
kubectl describe hpa mcp-server-hpa -n maxa-ds
```

### Useful Commands

```bash
# View all resources
kubectl get all -n maxa-ds

# Restart a deployment
kubectl rollout restart deployment/mcp-server -n maxa-ds

# Scale manually
kubectl scale deployment/celery-worker --replicas=10 -n maxa-ds

# View events
kubectl get events -n maxa-ds --sort-by='.lastTimestamp'

# Execute command in pod
kubectl exec -it <pod-name> -n maxa-ds -- /bin/bash

# Port forward for local testing
kubectl port-forward svc/mcp-server 8001:8001 -n maxa-ds
```

---

## MAINTENANCE

### Regular Tasks

**Daily:**
- Monitor dashboards for anomalies
- Check error logs

**Weekly:**
- Review resource utilization
- Check backup success
- Review cost reports

**Monthly:**
- Update dependencies
- Review and optimize costs
- Test disaster recovery procedures
- Security patches

**Quarterly:**
- Disaster recovery drill
- Capacity planning review
- Performance optimization
- Security audit

---

## NEXT STEPS

After successful deployment:

1. **Configure DNS**: Point your domain to the load balancer IP
2. **Set up SSL**: Let managed certificates provision (10-15 minutes)
3. **Configure Cursor**: Update Cursor MCP config with production URL
4. **Load Test**: Verify system handles expected load
5. **Train Team**: Ensure team knows how to operate and troubleshoot
6. **Monitor**: Set up alerts and dashboards
7. **Document**: Keep runbooks up to date

---

**End of Production Deployment Guide**
