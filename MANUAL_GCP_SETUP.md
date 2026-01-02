# Manual GCP Setup - Browser-Based Guide

This guide walks through setting up the Tournament Platform on Google Cloud Run. 
**Architecture:** Single Monolithic Service (Cloud Run) + Managed Database (Cloud SQL).

---

## Step 1: Enable Required APIs

**Console:** https://console.cloud.google.com/apis/library

Enable these APIs one by one:
- [ ] **Cloud Run Admin API** - Search "Cloud Run Admin API" → Enable
- [ ] **Cloud Build API** - Search "Cloud Build API" → Enable
- [ ] **Artifact Registry API** - Search "Artifact Registry API" → Enable
- [ ] **Cloud SQL Admin API** - Search "Cloud SQL Admin API" → Enable

**Time:** 5 minutes  
**Cost:** Free

---

## Step 2: Create Artifact Registry Repository

**Console:** https://console.cloud.google.com/artifacts

1. Click **"Create Repository"**
2. Configure:
   - **Name:** `tournament-repo`
   - **Format:** Docker
   - **Mode:** Standard
   - **Location type:** Region
   - **Region:** Choose your preferred region (e.g., `us-central1`)
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
   - **Zonal availability:** Single zone (cheaper for dev)
   
4. Click **"Show Configuration Options"**
   - **Machine type:** Shared core → `db-f1-micro` (1 vCPU, 0.6 GB)
   - **Storage type:** SSD
   - **Storage capacity:** 10 GB
   - **Connections:** Ensure **Public IP** is checked
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

**Time:** 10-15 minutes  
**Cost:** ~$7-10/month

---

## Step 4: Configure IAM Permissions

**Console:** https://console.cloud.google.com/iam-admin/serviceaccounts

1. Click **"Create Service Account"**
2. Configure:
   - **Service account name:** `tournament-runner`
   - **Description:** "Service account for tournament application"
   
3. Click **"Create and Continue"**

4. Grant these roles:
   - **Cloud SQL Client** - Allows connecting to Cloud SQL
   - **Artifact Registry Reader** - Allows pulling images (optional if same project)
   - Click **"Continue"** → **"Done"**

**Time:** 5 minutes  
**Cost:** Free

---

## Step 5: Verify and Document Your Configuration

Create a `.env.cloudrun` file with your values:

```bash
# Project Configuration
GCP_PROJECT_ID="your-project-id"
GCP_REGION="us-central1"
ARTIFACT_REPO="us-central1-docker.pkg.dev/your-project-id/tournament-repo"

# Database Configuration
DATABASE_URL="postgresql://tournament:YOUR_PASSWORD@/tournament_db?host=/cloudsql/PROJECT:REGION:tournament-db"

# Optional
SECRET_KEY="generate-a-random-secret-key"
```

---

## Next Steps: Build and Deploy

1. **Build and push Docker image:**
   ```bash
   source .env.cloudrun
   
   gcloud builds submit --tag ${ARTIFACT_REPO}/tournament-platform \
       -f Dockerfile.cloudrun.orchestrator .
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy tournament-platform \
       --image ${ARTIFACT_REPO}/tournament-platform \
       --region $GCP_REGION \
       --platform managed \
       --allow-unauthenticated \
       --service-account tournament-runner@$GCP_PROJECT_ID.iam.gserviceaccount.com \
       --add-cloudsql-instances YOUR_CONNECTION_NAME \
       --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_REGION=$GCP_REGION,DATABASE_URL=$DATABASE_URL"
   ```

3. **Get your URL:**
   ```bash
   gcloud run services describe tournament-platform \
       --region $GCP_REGION \
       --format 'value(status.url)'
   ```

---

## Cost Summary (Minimum Viable)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud SQL | db-f1-micro, 10GB | ~$7-10 |
| Cloud Run | On-demand CPU/Mem | Free tier usually covers low traffic |
| Artifact Registry | Storage | Pennies |
| **Total** | | **~$10/month** |

---

## Troubleshooting

### Can't connect to Cloud SQL
- Verify connection name format is correct
- Ensure Cloud SQL Client role is granted
- Check that `--add-cloudsql-instances` flag is used in deployment

### Permission denied errors
- Verify service account has Cloud Run Admin role
- Check that Service Account User role is granted
- Ensure you're using the correct service account in deployment

