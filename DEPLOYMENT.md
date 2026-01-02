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


## Troubleshooting

- **Database Connection:** Ensure the Cloud Run service account (`tournament-runner`) has the **Cloud SQL Client** role.
- **Migrations:** The application automatically creates tables on startup using `db.create_all()`. For production, consider using Flask-Migrate.
2. Check Memorystore IP is correct
3. Ensure firewall rules allow connection

### Database connection errors
1. Verify Cloud SQL connection string format
2. Check Cloud SQL Auth proxy if using public IP
3. Ensure Cloud Run has Cloud SQL Client role
