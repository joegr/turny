# Tournament Platform - Google Cloud Run Deployment Guide

## Architecture Overview

The platform deploys as two Cloud Run services:
- **tournament-orchestrator**: Main gateway, handles user requests, manages tournament lifecycle
- **tournament-service**: Dynamically deployed per tournament when published

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │   Cloud SQL  │    │          Cloud Run               │   │
│  │  PostgreSQL  │◄───┤                                  │   │
│  └──────────────┘    │  ┌────────────────────────────┐  │   │
│                      │  │  tournament-orchestrator   │  │   │
│  ┌──────────────┐    │  │  - User Dashboard          │  │   │
│  │  Memorystore │◄───┤  │  - Tournament Management   │  │   │
│  │    Redis     │    │  │  - Spawns tournament svc   │  │   │
│  └──────────────┘    │  └────────────────────────────┘  │   │
│                      │                │                  │   │
│                      │                ▼                  │   │
│                      │  ┌────────────────────────────┐  │   │
│                      │  │  tournament-{id} (dynamic) │  │   │
│                      │  │  - Match Engine            │  │   │
│                      │  │  - Real-time Results       │  │   │
│                      │  └────────────────────────────┘  │   │
│                      └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Cloud SQL PostgreSQL** instance
4. **Memorystore Redis** instance (or external Redis)

## Quick Start

### 1. Set Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export REDIS_URL="redis://10.0.0.1:6379"  # Your Memorystore IP
export DATABASE_URL="postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance"
```

### 2. Run Deployment Script

```bash
./deploy-cloudrun.sh
```

### 3. Grant Permissions for Dynamic Service Deployment

The orchestrator needs permission to create Cloud Run services:

```bash
# Get the service account
SERVICE_ACCOUNT=$(gcloud run services describe tournament-orchestrator \
    --region $GCP_REGION --format 'value(spec.template.spec.serviceAccountName)')

# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.admin"

# Grant Service Account User role (to act as the compute service account)
gcloud iam service-accounts add-iam-policy-binding \
    $GCP_PROJECT_ID-compute@developer.gserviceaccount.com \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/iam.serviceAccountUser"
```

## Manual Deployment Steps

### Build Images

```bash
# Build orchestrator
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/tournament-orchestrator \
    -f Dockerfile.cloudrun.orchestrator .

# Build tournament service
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/tournament-service \
    -f Dockerfile.cloudrun.tournament .
```

### Deploy Orchestrator

```bash
gcloud run deploy tournament-orchestrator \
    --image gcr.io/$GCP_PROJECT_ID/tournament-orchestrator \
    --region $GCP_REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars "USE_CLOUD_RUN=true" \
    --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID" \
    --set-env-vars "GCP_REGION=$GCP_REGION" \
    --set-env-vars "TOURNAMENT_SERVICE_IMAGE=gcr.io/$GCP_PROJECT_ID/tournament-service:latest" \
    --set-env-vars "REDIS_URL=$REDIS_URL" \
    --set-env-vars "DATABASE_URL=$DATABASE_URL"
```

## Setting Up Cloud SQL

```bash
# Create PostgreSQL instance
gcloud sql instances create tournament-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$GCP_REGION

# Create database
gcloud sql databases create tournament_db --instance=tournament-db

# Create user
gcloud sql users create tournament \
    --instance=tournament-db \
    --password=your-secure-password

# Get connection name
gcloud sql instances describe tournament-db --format='value(connectionName)'
```

## Setting Up Memorystore Redis

```bash
# Create Redis instance
gcloud redis instances create tournament-redis \
    --size=1 \
    --region=$GCP_REGION \
    --redis-version=redis_7_0

# Get the IP address
gcloud redis instances describe tournament-redis \
    --region=$GCP_REGION \
    --format='value(host)'
```

Note: Memorystore requires a VPC connector for Cloud Run access:

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create tournament-connector \
    --region=$GCP_REGION \
    --range=10.8.0.0/28

# Update Cloud Run service to use connector
gcloud run services update tournament-orchestrator \
    --region=$GCP_REGION \
    --vpc-connector=tournament-connector
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `USE_CLOUD_RUN` | Enable Cloud Run mode | Yes |
| `GCP_PROJECT_ID` | Your GCP project ID | Yes |
| `GCP_REGION` | Cloud Run region | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `TOURNAMENT_SERVICE_IMAGE` | Tournament service container image | Yes |
| `SECRET_KEY` | Flask secret key | Recommended |

## Cost Optimization

- Set `min-instances=0` to scale to zero when idle
- Use `--cpu-throttling` to reduce costs during low traffic
- Tournament services auto-delete after archival

## Monitoring

View logs:
```bash
gcloud logging read "resource.type=cloud_run_revision" --project=$GCP_PROJECT_ID
```

View deployed services:
```bash
gcloud run services list --region=$GCP_REGION
```

## Troubleshooting

### Tournament service not deploying
1. Check orchestrator logs for Cloud Run API errors
2. Verify IAM permissions are set correctly
3. Ensure TOURNAMENT_SERVICE_IMAGE is correct

### Redis connection timeout
1. Verify VPC connector is configured
2. Check Memorystore IP is correct
3. Ensure firewall rules allow connection

### Database connection errors
1. Verify Cloud SQL connection string format
2. Check Cloud SQL Auth proxy if using public IP
3. Ensure Cloud Run has Cloud SQL Client role
