# GCP Setup Guide - Step by Step

This guide walks through provisioning GCP resources one by one for the Tournament Platform.

## Prerequisites

- `gcloud` CLI installed and authenticated
- GCP project with billing enabled
- Project ID ready

## Quick Setup (Automated)

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"  # or your preferred region
./setup-gcp-resources.sh
```

This script handles all 6 steps automatically. If you prefer manual control, follow the steps below.

---

## Manual Setup (Step by Step)

### Step 1: Enable Required APIs

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    vpcaccess.googleapis.com \
    compute.googleapis.com \
    --project=$GCP_PROJECT_ID
```

**Time:** ~1 minute  
**Cost:** Free

---

### Step 2: Create Cloud SQL PostgreSQL

```bash
# Create instance (takes 5-10 minutes)
gcloud sql instances create tournament-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$GCP_REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup \
    --project=$GCP_PROJECT_ID

# Create database
gcloud sql databases create tournament_db \
    --instance=tournament-db \
    --project=$GCP_PROJECT_ID

# Create user (save this password!)
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
**Save:** Connection name for DATABASE_URL

---

### Step 3: Create VPC Network

```bash
gcloud compute networks create tournament-vpc \
    --subnet-mode=auto \
    --project=$GCP_PROJECT_ID
```

**Time:** ~30 seconds  
**Cost:** Free (data transfer charges apply)

---

### Step 4: Create Memorystore Redis

```bash
# Create Redis instance (takes 5-10 minutes)
gcloud redis instances create tournament-redis \
    --size=1 \
    --region=$GCP_REGION \
    --redis-version=redis_7_0 \
    --network=tournament-vpc \
    --project=$GCP_PROJECT_ID

# Get Redis host and port
gcloud redis instances describe tournament-redis \
    --region=$GCP_REGION \
    --project=$GCP_PROJECT_ID \
    --format='value(host,port)'
```

**Time:** 5-10 minutes  
**Cost:** ~$35/month (1GB Basic Tier)  
**Save:** Host and port for REDIS_URL

**Alternative:** Use external Redis (Upstash, Redis Cloud) to save costs:
- Upstash: Free tier available
- Redis Cloud: Free 30MB tier

---

### Step 5: Create VPC Connector

Cloud Run needs this to access Memorystore Redis in the VPC.

```bash
gcloud compute networks vpc-access connectors create tournament-connector \
    --region=$GCP_REGION \
    --network=tournament-vpc \
    --range=10.8.0.0/28 \
    --project=$GCP_PROJECT_ID
```

**Time:** 2-3 minutes  
**Cost:** ~$10/month (always-on connector)

**Skip if using external Redis** - you won't need VPC access.

---

### Step 6: Create Service Account & IAM Permissions

```bash
# Create service account
gcloud iam service-accounts create tournament-orchestrator \
    --display-name="Tournament Orchestrator Service Account" \
    --project=$GCP_PROJECT_ID

# Grant Cloud Run Admin (to deploy tournament services)
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="serviceAccount:tournament-orchestrator@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

# Grant Cloud SQL Client (to connect to database)
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="serviceAccount:tournament-orchestrator@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# Grant Service Account User (to act as compute SA)
gcloud iam service-accounts add-iam-policy-binding \
    $GCP_PROJECT_ID-compute@developer.gserviceaccount.com \
    --member="serviceAccount:tournament-orchestrator@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --project=$GCP_PROJECT_ID
```

**Time:** ~1 minute  
**Cost:** Free

---

## Environment Variables

After provisioning, set these before deploying:

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# From Cloud SQL
export DATABASE_URL="postgresql://tournament:YOUR_PASSWORD@/tournament_db?host=/cloudsql/PROJECT:REGION:tournament-db"

# From Memorystore Redis
export REDIS_URL="redis://10.x.x.x:6379"

# Or if using external Redis
export REDIS_URL="redis://your-external-redis:6379"
```

---

## Cost Estimates

| Resource | Tier | Monthly Cost |
|----------|------|--------------|
| Cloud SQL (db-f1-micro) | 1 vCPU, 0.6GB RAM | ~$7-10 |
| Memorystore Redis | 1GB Basic | ~$35 |
| VPC Connector | Always-on | ~$10 |
| Cloud Run (orchestrator) | Pay per use | ~$0-5 |
| Cloud Run (tournament services) | Pay per use | ~$0-10 |
| **Total** | | **~$52-70/month** |

**Cost Optimization:**
- Use external Redis (Upstash free tier) → Save $35/month
- Use Cloud SQL shared-core → Already cheapest option
- Set Cloud Run min-instances=0 → Pay only when active

---

## Next Steps

Once resources are provisioned:

```bash
# Deploy to Cloud Run
./deploy-cloudrun.sh
```

See `DEPLOYMENT.md` for full deployment documentation.

---

## Troubleshooting

### "API not enabled"
Run Step 1 again to enable all APIs.

### "VPC connector creation failed"
Ensure the IP range `10.8.0.0/28` doesn't conflict with existing subnets.

### "Permission denied"
Verify you have Owner or Editor role on the project.

### "Quota exceeded"
Check GCP quotas in Console → IAM & Admin → Quotas.
