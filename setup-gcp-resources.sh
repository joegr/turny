#!/bin/bash
set -e

# GCP Resource Provisioning Script for Tournament Platform
# Run each section individually as needed

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Set GCP_PROJECT_ID or configure default project"
    exit 1
fi

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# =============================================================================
# STEP 1: Enable Required APIs
# =============================================================================
echo "=== STEP 1: Enabling Required APIs ==="
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    vpcaccess.googleapis.com \
    compute.googleapis.com \
    --project=$PROJECT_ID

echo "✓ APIs enabled"
echo ""

# =============================================================================
# STEP 1.5: Create Artifact Registry Repository
# =============================================================================
echo "=== STEP 1.5: Creating Artifact Registry Repository ==="
if gcloud artifacts repositories describe tournament-repo \
    --project=$PROJECT_ID \
    --location=$REGION 2>/dev/null; then
    echo "✓ Repository 'tournament-repo' already exists"
else
    gcloud artifacts repositories create tournament-repo \
        --project=$PROJECT_ID \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker repository for Tournament Platform"
    
    echo "✓ Repository created"
fi
echo ""

# =============================================================================
# STEP 2: Create Cloud SQL PostgreSQL Instance
# =============================================================================
echo "=== STEP 2: Creating Cloud SQL PostgreSQL Instance ==="
echo "This will take 5-10 minutes..."

# Check if instance exists
if gcloud sql instances describe tournament-db --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Cloud SQL instance 'tournament-db' already exists"
else
    gcloud sql instances create tournament-db \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=10GB \
        --backup \
        --project=$PROJECT_ID
    
    echo "✓ Cloud SQL instance created"
fi

# Create database
echo "Creating database..."
gcloud sql databases create tournament_db \
    --instance=tournament-db \
    --project=$PROJECT_ID 2>/dev/null || echo "Database already exists"

# Create user
echo "Creating database user..."
DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create tournament \
    --instance=tournament-db \
    --password="$DB_PASSWORD" \
    --project=$PROJECT_ID 2>/dev/null || echo "User already exists"

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe tournament-db \
    --project=$PROJECT_ID \
    --format='value(connectionName)')

echo "✓ Cloud SQL setup complete"
echo "  Connection name: $CONNECTION_NAME"
echo "  Database: tournament_db"
echo "  User: tournament"
echo "  Password: $DB_PASSWORD"
echo ""
echo "DATABASE_URL for Cloud Run:"
echo "postgresql://tournament:$DB_PASSWORD@/tournament_db?host=/cloudsql/$CONNECTION_NAME"
echo ""

# =============================================================================
# STEP 3: Create VPC Network (for Memorystore)
# =============================================================================
echo "=== STEP 3: Creating VPC Network ==="

# Check if network exists
if gcloud compute networks describe tournament-vpc --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ VPC 'tournament-vpc' already exists"
else
    gcloud compute networks create tournament-vpc \
        --subnet-mode=auto \
        --project=$PROJECT_ID
    
    echo "✓ VPC network created"
fi

# =============================================================================
# STEP 4: Create Memorystore Redis Instance
# =============================================================================
echo "=== STEP 4: Creating Memorystore Redis Instance ==="
echo "This will take 5-10 minutes..."

# Check if instance exists
if gcloud redis instances describe tournament-redis --region=$REGION --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Redis instance 'tournament-redis' already exists"
else
    gcloud redis instances create tournament-redis \
        --size=1 \
        --region=$REGION \
        --redis-version=redis_7_0 \
        --network=tournament-vpc \
        --project=$PROJECT_ID
    
    echo "✓ Redis instance created"
fi

# Get Redis IP
REDIS_HOST=$(gcloud redis instances describe tournament-redis \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(host)')

REDIS_PORT=$(gcloud redis instances describe tournament-redis \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(port)')

echo "✓ Redis setup complete"
echo "  Host: $REDIS_HOST"
echo "  Port: $REDIS_PORT"
echo ""
echo "REDIS_URL for Cloud Run:"
echo "redis://$REDIS_HOST:$REDIS_PORT"
echo ""

# =============================================================================
# STEP 5: Create VPC Connector (for Cloud Run to access Redis)
# =============================================================================
echo "=== STEP 5: Creating VPC Connector ==="

# Check if connector exists
if gcloud compute networks vpc-access connectors describe tournament-connector \
    --region=$REGION --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ VPC connector 'tournament-connector' already exists"
else
    gcloud compute networks vpc-access connectors create tournament-connector \
        --region=$REGION \
        --network=tournament-vpc \
        --range=10.8.0.0/28 \
        --project=$PROJECT_ID
    
    echo "✓ VPC connector created"
fi

# =============================================================================
# STEP 6: Create Service Account for Orchestrator
# =============================================================================
echo "=== STEP 6: Creating Service Account ==="

SERVICE_ACCOUNT="tournament-orchestrator@$PROJECT_ID.iam.gserviceaccount.com"

# Check if service account exists
if gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Service account already exists"
else
    gcloud iam service-accounts create tournament-orchestrator \
        --display-name="Tournament Orchestrator Service Account" \
        --project=$PROJECT_ID
    
    echo "✓ Service account created"
fi

# Grant necessary roles
echo "Granting IAM roles..."

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.admin" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/cloudsql.client" \
    --condition=None

gcloud iam service-accounts add-iam-policy-binding \
    $PROJECT_ID-compute@developer.gserviceaccount.com \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/iam.serviceAccountUser" \
    --project=$PROJECT_ID

echo "✓ IAM roles granted"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo "========================================="
echo "GCP Resources Provisioned Successfully!"
echo "========================================="
echo ""
echo "Export these environment variables before deploying:"
echo ""
echo "export GCP_PROJECT_ID=\"$PROJECT_ID\""
echo "export GCP_REGION=\"$REGION\""
echo "export DATABASE_URL=\"postgresql://tournament:$DB_PASSWORD@/tournament_db?host=/cloudsql/$CONNECTION_NAME\""
echo "export REDIS_URL=\"redis://$REDIS_HOST:$REDIS_PORT\""
echo ""
echo "Next step: Run ./deploy-cloudrun.sh"
