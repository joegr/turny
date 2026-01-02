# GCP Setup Guide - Step by Step

This guide walks through provisioning GCP resources for the **Tournament Platform Monolith**.

## Architecture

- **App Service:** Cloud Run (Single container)
- **Database:** Cloud SQL (PostgreSQL)
- **Networking:** Standard (Public IP with Cloud SQL Auth Proxy)

## Prerequisites

- `gcloud` CLI installed and authenticated
- GCP project with billing enabled
- Project ID ready

## Quick Setup (Automated)

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
./setup-gcp-resources.sh
```

This script handles API enablement, Artifact Registry creation, Cloud SQL setup, and IAM permissions.

---

## Manual Setup (Step by Step)

### Step 1: Enable Required APIs

```bash
export GCP_PROJECT_ID="your-project-id"

gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    sqladmin.googleapis.com \
    compute.googleapis.com \
    --project=$GCP_PROJECT_ID
```

**Time:** ~1 minute  
**Cost:** Free

---

### Step 2: Create Cloud SQL PostgreSQL

```bash
export GCP_REGION="us-central1"

# Create instance
gcloud sql instances create tournament-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$GCP_REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --project=$GCP_PROJECT_ID

# Create database
gcloud sql databases create tournament_db \
    --instance=tournament-db \
    --project=$GCP_PROJECT_ID

# Create user
gcloud sql users create tournament \
    --instance=tournament-db \
    --password="YOUR_SECURE_PASSWORD" \
    --project=$GCP_PROJECT_ID

# Get connection name
gcloud sql instances describe tournament-db \
    --project=$GCP_PROJECT_ID \
    --format='value(connectionName)'
```

**Time:** 5-10 minutes  
**Cost:** ~$7-10/month (db-f1-micro)

---

### Step 3: Configure IAM Permissions

Create a service account for the application to access Cloud SQL.

```bash
# Create service account
gcloud iam service-accounts create tournament-runner \
    --display-name="Tournament Runner" \
    --project=$GCP_PROJECT_ID

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="serviceAccount:tournament-runner@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
```

---

## Environment Variables for Deployment

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export DATABASE_URL="postgresql://tournament:YOUR_PASSWORD@/tournament_db?host=/cloudsql/PROJECT:REGION:INSTANCE"
```

## Next Steps

Run the deployment script:

```bash
./deploy-cloudrun.sh
```
