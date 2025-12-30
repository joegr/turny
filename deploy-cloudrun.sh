#!/bin/bash
set -e

# Tournament Platform - Google Cloud Run Deployment Script (Monolith)
# Prerequisites:
# 1. gcloud CLI installed and authenticated
# 2. A GCP project with billing enabled
# 3. Cloud Run API enabled
# 4. PostgreSQL (Cloud SQL) instance

echo "=== Tournament Platform Cloud Run Deployment ==="

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"
DATABASE_URL="${DATABASE_URL:-}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID not set and no default project configured"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "Warning: DATABASE_URL not set. You'll need to set this in Cloud Run."
fi

echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=$PROJECT_ID

# Build and push image
echo "Building platform image..."
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/tournament-repo/tournament-platform \
    --project=$PROJECT_ID \
    -f Dockerfile.cloudrun.orchestrator .

# Deploy service
echo "Deploying to Cloud Run..."
gcloud run deploy tournament-platform \
    --image us-central1-docker.pkg.dev/$PROJECT_ID/tournament-repo/tournament-platform \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,DATABASE_URL=$DATABASE_URL" \
    --project=$PROJECT_ID

# Get URL
SERVICE_URL=$(gcloud run services describe tournament-platform \
    --region $REGION \
    --project=$PROJECT_ID \
    --format 'value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Ensure Cloud SQL is running and accessible"
echo "2. Check the URL to see your running application"

