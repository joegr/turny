# Manual GCP Setup - Browser-Based Guide

This guide walks through setting up each GCP service manually via the Cloud Console, following Google Cloud best practices.

---

## Step 1: Enable Required APIs

**Console:** https://console.cloud.google.com/apis/library

Enable these APIs one by one:
- [ ] **Cloud Run Admin API** - Search "Cloud Run Admin API" → Enable
- [ ] **Cloud Build API** - Search "Cloud Build API" → Enable
- [ ] **Artifact Registry API** - Search "Artifact Registry API" → Enable (Replaces Container Registry)
- [ ] **Cloud SQL Admin API** - Search "Cloud SQL Admin API" → Enable
- [ ] **Memorystore for Redis API** - Search "Memorystore for Redis API" → Enable
- [ ] **Serverless VPC Access API** - Search "Serverless VPC Access API" → Enable
- [ ] **Compute Engine API** - Search "Compute Engine API" → Enable

**Time:** 5 minutes  
**Cost:** Free

---

## Step 2: Create Artifact Registry Repository

Google Container Registry (gcr.io) is deprecated. Use Artifact Registry for storing Docker images.

**Console:** https://console.cloud.google.com/artifacts

1. Click **"Create Repository"**
2. Configure:
   - **Name:** `tournament-repo`
   - **Format:** Docker
   - **Mode:** Standard
   - **Location type:** Region
   - **Region:** Choose your preferred region (e.g., `us-central1`)
     *Important: Keep this consistent with your other services.*
3. Click **"Create"**

**Save this image path prefix:**
```
us-central1-docker.pkg.dev/YOUR_PROJECT_ID/tournament-repo
```

**Time:** 2 minutes
**Cost:** Free (storage costs apply for images)

---

## Step 3: Create Cloud SQL PostgreSQL Instance

**Console:** https://console.cloud.google.com/sql/instances

1. Click **"Create Instance"**
2. Choose **"PostgreSQL"**
3. Configure:
   - **Instance ID:** `tournament-db`
   - **Password:** Set a strong password (save this!)
   - **Database version:** PostgreSQL 15
   - **Region:** Same as Artifact Registry (e.g., `us-central1`)
   - **Zonal availability:** Single zone (cheaper for dev, use HA for prod)
   
4. Click **"Show Configuration Options"**
   - **Machine type:** Shared core → `db-f1-micro` (1 vCPU, 0.6 GB)
   - **Storage type:** SSD
   - **Storage capacity:** 10 GB
   - **Connections:** Ensure **Public IP** is checked (required for standard Cloud Run connection without Private Service Connect). 
     *Note: This allows access via authorized networks. Cloud Run uses the Cloud SQL Auth Proxy which connects securely.*
   - **Enable automatic backups:** Yes

5. Click **"Create Instance"** (takes 5-10 minutes)

6. Once created, click on the instance name
7. Go to **"Databases"** tab → Click **"Create Database"**
   - **Database name:** `tournament_db`
   - Click **"Create"**

8. Go to **"Users"** tab → Click **"Add User Account"**
   - **User name:** `tournament`
   - **Password:** Set a strong password (save this!)
   - Click **"Add"**

9. Go to **"Overview"** tab
   - **Copy the "Connection name"** (format: `project-id:region:instance-name`)

**Save these values:**
```
Connection Name: ___________________________________
Database: tournament_db
User: tournament
Password: ___________________________________
```

**DATABASE_URL format (Unix Socket):**
```
postgresql://tournament:YOUR_PASSWORD@/tournament_db?host=/cloudsql/YOUR_CONNECTION_NAME
```
*Note: This Unix socket format is specific to Cloud Run.*

**Time:** 10-15 minutes  
**Cost:** ~$7-10/month

---

## Step 4: Choose Redis Option

You have two options for Redis:

### Option A: Memorystore Redis (GCP-managed, more expensive)

**Console:** https://console.cloud.google.com/memorystore/redis/instances

1. Click **"Create Instance"**
2. Configure:
   - **Instance ID:** `tournament-redis`
   - **Tier:** Basic
   - **Capacity:** 1 GB
   - **Region:** Same as Cloud SQL (e.g., `us-central1`)
   - **Redis version:** 7.0
   - **Network:** default
   - **Connection mode:** Direct peering

3. Click **"Create"** (takes 5-10 minutes)

4. Once created, note the **IP address** and **port** (usually 6379)

**REDIS_URL format:** `redis://YOUR_REDIS_HOST:6379`

**Time:** 10-15 minutes  
**Cost:** ~$35/month  
**Note:** Requires VPC connector (Step 5)

---

### Option B: External Redis (Recommended for cost savings)

**Upstash (Free tier available):** https://upstash.com

1. Sign up for Upstash
2. Click **"Create Database"**
3. Configure:
   - **Region:** Choose AWS/GCP region closest to your Cloud Run region
   - **TLS:** Enabled

4. Copy the **Redis URL** from the dashboard

**Time:** 5 minutes  
**Cost:** Free tier available  
**Note:** Skip Step 5 (VPC connector) if using external Redis

---

## Step 5: Create VPC Connector (Only if using Memorystore)

**Skip this step if using external Redis.**

**Console:** https://console.cloud.google.com/networking/connectors

1. Click **"Create Connector"**
2. Configure:
   - **Name:** `tournament-connector`
   - **Region:** Same as your Cloud Run/Redis region
   - **Network:** default
   - **Subnet:** Create new subnet
   - **IP range:** `10.8.0.0/28` (Must not overlap with existing subnets)
   - **Min instances:** 2
   - **Max instances:** 3
   - **Machine type:** f1-micro

3. Click **"Create"** (takes 2-3 minutes)

**Time:** 5 minutes  
**Cost:** ~$10/month

---

## Step 6: Configure IAM Permissions

**Console:** https://console.cloud.google.com/iam-admin/serviceaccounts

### Create Service Account

1. Click **"Create Service Account"**
2. Configure:
   - **Service account name:** `tournament-orchestrator`
   - **Description:** "Service account for tournament orchestrator"
   
3. Click **"Create and Continue"**

4. Grant these roles:
   - **Cloud Run Admin** - Allows deploying tournament services
   - **Cloud SQL Client** - Allows connecting to Cloud SQL
   - **Service Account User** - Allows deploying services as this service account
   - Click **"Continue"** → **"Done"**

**Time:** 5 minutes  
**Cost:** Free

---

## Step 7: Verify and Document Your Configuration

Create a `.env.cloudrun` file with your values:

```bash
# Project Configuration
GCP_PROJECT_ID="your-project-id"
GCP_REGION="us-central1"
ARTIFACT_REPO="us-central1-docker.pkg.dev/your-project-id/tournament-repo"

# Database Configuration
DATABASE_URL="postgresql://tournament:YOUR_PASSWORD@/tournament_db?host=/cloudsql/PROJECT:REGION:tournament-db"

# Redis Configuration (choose one)
# Option A: Memorystore
REDIS_URL="redis://10.x.x.x:6379"

# Option B: External (Upstash)
# REDIS_URL="rediss://default:YOUR_TOKEN@YOUR_ENDPOINT.upstash.io:6379"

# Cloud Run Configuration
USE_CLOUD_RUN="true"
TOURNAMENT_SERVICE_IMAGE="${ARTIFACT_REPO}/tournament-service:latest"

# Optional
SECRET_KEY="generate-a-random-secret-key"
```

---

## Next Steps: Build and Deploy

1. **Build and push Docker images to Artifact Registry:**
   ```bash
   source .env.cloudrun
   
   # Submit builds to Cloud Build
   gcloud builds submit --tag ${ARTIFACT_REPO}/tournament-orchestrator \
       -f Dockerfile.cloudrun.orchestrator .
   
   gcloud builds submit --tag ${ARTIFACT_REPO}/tournament-service \
       -f Dockerfile.cloudrun.tournament .
   ```

2. **Deploy orchestrator:**
   ```bash
   gcloud run deploy tournament-orchestrator \
       --image ${ARTIFACT_REPO}/tournament-orchestrator \
       --region $GCP_REGION \
       --platform managed \
       --allow-unauthenticated \
       --service-account tournament-orchestrator@$GCP_PROJECT_ID.iam.gserviceaccount.com \
       --add-cloudsql-instances YOUR_CONNECTION_NAME \
       --set-env-vars "USE_CLOUD_RUN=true,GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION,TOURNAMENT_SERVICE_IMAGE=${ARTIFACT_REPO}/tournament-service:latest,REDIS_URL=$REDIS_URL,DATABASE_URL=$DATABASE_URL"
   ```

   **If using Memorystore, add:**
   ```bash
   --vpc-connector tournament-connector
   ```

---

## Cost Summary

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud SQL | db-f1-micro, 10GB | $7-10 |
| Redis (Memorystore) | 1GB Basic | $35 |
| Redis (Upstash) | Free tier | $0 |
| VPC Connector | f1-micro | $10 |
| Cloud Run (orchestrator) | Pay per use | $0-5 |
| Cloud Run (tournaments) | Pay per use | $0-10 |

**Total with Memorystore:** ~$52-70/month  
**Total with Upstash:** ~$17-25/month (60% savings!)

---

## Troubleshooting

### Can't connect to Cloud SQL
- Verify connection name format is correct
- Ensure Cloud SQL Client role is granted
- Check that `--add-cloudsql-instances` flag is used in deployment

### Can't connect to Redis (Memorystore)
- Verify VPC connector is created and attached
- Check Redis IP address is correct
- Ensure Redis and VPC connector are in same region

### Permission denied errors
- Verify service account has Cloud Run Admin role
- Check that Service Account User role is granted
- Ensure you're using the correct service account in deployment

### Tournament services not deploying
- Check orchestrator logs: `gcloud run logs read --service tournament-orchestrator`
- Verify TOURNAMENT_SERVICE_IMAGE environment variable is set
- Ensure service account has Cloud Run Admin permissions
