# GCP Console Manual Setup Guide

Step-by-step instructions to set up GCP resources via the Google Cloud Console.

## Prerequisites
- GCP Project created
- Billing enabled
- GitHub repository connected to Cloud Build

---

## Step 1: Enable APIs

Go to **APIs & Services > Enable APIs and Services**

Enable these APIs:
1. **Cloud Run API**
2. **Cloud Build API**
3. **Artifact Registry API**
4. **Cloud SQL Admin API**
5. **Secret Manager API**
6. **Compute Engine API**

---

## Step 2: Create Artifact Registry Repository

Go to **Artifact Registry > Repositories > Create Repository**

| Field | Value |
|-------|-------|
| Name | `turny` |
| Format | Docker |
| Mode | Standard |
| Location type | Region |
| Region | `us-central1` |

Click **Create**

---

## Step 3: Create Cloud SQL Instance

Go to **SQL > Create Instance > Choose PostgreSQL**

| Field | Value |
|-------|-------|
| Instance ID | `tournament-db` |
| Password | (set root password, save it) |
| Database version | PostgreSQL 15 |
| Region | `us-central1` |
| Machine type | `db-f1-micro` (cheapest) |
| Storage | SSD, 10GB |

Click **Create Instance** (takes 5-10 minutes)

### Create Database
After instance is ready:
1. Click on `tournament-db` instance
2. Go to **Databases** tab
3. Click **Create Database**
4. Name: `tournament_db`

### Create User
1. Go to **Users** tab
2. Click **Add User Account**
3. Username: `tournament`
4. Password: (generate and save securely)

---

## Step 4: Create Secret in Secret Manager

Go to **Security > Secret Manager > Create Secret**

| Field | Value |
|-------|-------|
| Name | `tournament-db-pass` |
| Secret value | (paste the DB user password from Step 3) |

Click **Create Secret**

---

## Step 5: Create Service Account

Go to **IAM & Admin > Service Accounts > Create Service Account**

| Field | Value |
|-------|-------|
| Name | `tournament-runner` |
| ID | `tournament-runner` |

Click **Create and Continue**

### Grant Roles
Add these roles:
- `Cloud SQL Client`
- `Artifact Registry Reader`
- `Secret Manager Secret Accessor`

Click **Done**

---

## Step 6: Grant Cloud Build Permissions

Go to **IAM & Admin > IAM**

Find the Cloud Build service account: `[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`

Click **Edit** (pencil icon) and add these roles:
- `Cloud SQL Client`
- `Secret Manager Secret Accessor`
- `Cloud Run Admin`
- `Service Account User`

Click **Save**

---

## Step 7: Verify Cloud Build Trigger

Go to **Cloud Build > Triggers**

Your trigger `turnydeploy` should be configured with:
- **Event**: Push to branch `main`
- **Configuration**: `cloudbuild.yaml`

---

## Step 8: Test Deployment

Push to main branch:
```bash
git add -A && git commit -m "Deploy" && git push
```

Monitor at **Cloud Build > History**

---

## Troubleshooting

### "Repository not found"
- Verify Artifact Registry repo `turny` exists in `us-central1`

### "Secret not found"
- Verify secret `tournament-db-pass` exists in Secret Manager
- Verify Cloud Build SA has `Secret Manager Secret Accessor` role

### "Cloud SQL connection failed"
- Verify Cloud SQL instance `tournament-db` is running
- Verify Cloud Build SA has `Cloud SQL Client` role

### "Permission denied deploying to Cloud Run"
- Verify Cloud Build SA has `Cloud Run Admin` and `Service Account User` roles
