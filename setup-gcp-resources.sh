#!/bin/bash
set -e

# GCP Resource Provisioning Script for Tournament Platform (Monolith)
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
        --project=$PROJECT_ID \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=10GB \
        --root-password=tournament123 \
        --assign-ip
    
    echo "✓ Cloud SQL instance created"
fi

# Create database if not exists
if gcloud sql databases describe tournament_db --instance=tournament-db --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Database 'tournament_db' already exists"
else
    gcloud sql databases create tournament_db --instance=tournament-db --project=$PROJECT_ID
    echo "✓ Database 'tournament_db' created"
fi

# Create user if not exists
if gcloud sql users describe tournament --instance=tournament-db --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ User 'tournament' already exists"
else
    gcloud sql users create tournament \
        --instance=tournament-db \
        --project=$PROJECT_ID \
        --password=tournament123
    echo "✓ User 'tournament' created"
fi

CONNECTION_NAME=$(gcloud sql instances describe tournament-db --project=$PROJECT_ID --format="value(connectionName)")
echo "Connection Name: $CONNECTION_NAME"
echo ""

# =============================================================================
# STEP 3: Configure IAM Permissions
# =============================================================================
echo "=== STEP 3: Configure IAM Permissions ==="

# Create service account
SA_NAME="tournament-runner"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Service account '$SA_NAME' already exists"
else
    gcloud iam service-accounts create $SA_NAME \
        --description="Service account for Tournament Platform" \
        --display-name="Tournament Runner" \
        --project=$PROJECT_ID
    echo "✓ Service account created"
fi

# Grant roles
echo "Granting roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudsql.client" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/artifactregistry.reader" >/dev/null

echo "✓ Roles granted"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo "=== Setup Complete ==="
echo ""
echo "Resources created:"
echo "1. Artifact Registry: tournament-repo"
echo "2. Cloud SQL: tournament-db (Connection: $CONNECTION_NAME)"
echo "3. Service Account: $SA_EMAIL"
echo ""
echo "DATABASE_URL for Cloud Run:"
echo "postgresql://tournament:tournament123@/tournament_db?host=/cloudsql/$CONNECTION_NAME"
echo ""
echo "You can now run deploy-cloudrun.sh to deploy the application."
