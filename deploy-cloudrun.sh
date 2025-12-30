#!/bin/bash
set -e

# Tournament Platform - Google Cloud Run Deployment Script
# Prerequisites:
# 1. gcloud CLI installed and authenticated
# 2. A GCP project with billing enabled
# 3. Cloud Run API enabled
# 4. Redis (Memorystore) and PostgreSQL (Cloud SQL) instances

echo "=== Tournament Platform Cloud Run Deployment ==="

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"
REDIS_URL="${REDIS_URL:-}"
DATABASE_URL="${DATABASE_URL:-}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID not set and no default project configured"
    exit 1
fi

if [ -z "$REDIS_URL" ]; then
    echo "Warning: REDIS_URL not set. You'll need to set this in Cloud Run."
fi

if [ -z "$DATABASE_URL" ]; then
    echo "Warning: DATABASE_URL not set. You'll need to set this in Cloud Run."
fi

echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable run.googleapis.com containerregistry.googleapis.com cloudbuild.googleapis.com --project=$PROJECT_ID

# Build and push orchestrator image
echo "Building orchestrator image..."
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/tournament-repo/tournament-orchestrator \
    --project=$PROJECT_ID \
    -f Dockerfile.cloudrun.orchestrator .

# Build and push tournament service image
echo "Building tournament service image..."
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/tournament-repo/tournament-service \
    --project=$PROJECT_ID \
    -f Dockerfile.cloudrun.tournament .

# Deploy orchestrator
echo "Deploying orchestrator to Cloud Run..."
gcloud run deploy tournament-orchestrator \
    --image us-central1-docker.pkg.dev/$PROJECT_ID/tournament-repo/tournament-orchestrator \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "USE_CLOUD_RUN=true,GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,TOURNAMENT_SERVICE_IMAGE=us-central1-docker.pkg.dev/$PROJECT_ID/tournament-repo/tournament-service:latest" \
    --set-env-vars "REDIS_URL=$REDIS_URL,DATABASE_URL=$DATABASE_URL" \
    --project=$PROJECT_ID

# Get orchestrator URL
ORCHESTRATOR_URL=$(gcloud run services describe tournament-orchestrator \
    --region $REGION \
    --project=$PROJECT_ID \
    --format 'value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Orchestrator URL: $ORCHESTRATOR_URL"
echo ""
echo "Next steps:"
echo "1. Set up Cloud SQL for PostgreSQL (if not done)"
echo "2. Set up Memorystore for Redis (if not done)"
echo "3. Update environment variables with connection strings"
echo "4. Grant the orchestrator's service account permission to deploy Cloud Run services"
echo ""
echo "To grant permissions for dynamic tournament service deployment:"
echo "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "    --member=serviceAccount:$PROJECT_ID-compute@developer.gserviceaccount.com \\"
echo "    --role=roles/run.admin"
