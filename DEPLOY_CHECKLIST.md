# GCP Deployment Checklist

Complete these steps in the Google Cloud Console before deploying.

## 1. Enable APIs
Go to **APIs & Services > Enable APIs**
- [ ] Cloud Run API
- [ ] Cloud Build API
- [ ] Artifact Registry API
- [ ] Cloud SQL Admin API
- [ ] Secret Manager API

## 2. Create Artifact Registry Repository
Go to **Artifact Registry > Create Repository**
- [ ] Name: `turny`
- [ ] Format: Docker
- [ ] Region: `us-central1`

## 3. Create Cloud SQL Instance
Go to **SQL > Create Instance > PostgreSQL**
- [ ] Instance ID: `tournament-db`
- [ ] Database version: PostgreSQL 15
- [ ] Region: `us-central1`
- [ ] Machine type: `db-f1-micro`
- [ ] Create database: `tournament_db`
- [ ] Create user: `tournament` (save password)

## 4. Create Secrets in Secret Manager
Go to **Security > Secret Manager > Create Secret**

- [ ] `tournament-db-pass` - Your Cloud SQL user password
- [ ] `flask-secret-key` - Random string (use: `openssl rand -hex 32`)

## 5. Create Service Account
Go to **IAM & Admin > Service Accounts > Create**
- [ ] Name: `tournament-runner`
- [ ] Grant roles:
  - Cloud SQL Client
  - Artifact Registry Reader
  - Secret Manager Secret Accessor

## 6. Grant Cloud Build Permissions
Go to **IAM & Admin > IAM**, find `{PROJECT_NUMBER}@cloudbuild.gserviceaccount.com`
- [ ] Cloud SQL Client
- [ ] Secret Manager Secret Accessor
- [ ] Cloud Run Admin
- [ ] Service Account User

## 7. Create Cloud Build Trigger
Go to **Cloud Build > Triggers > Create Trigger**
- [ ] Name: `turnydeploy`
- [ ] Event: Push to branch
- [ ] Source: Connect GitHub repo
- [ ] Branch: `^main$`
- [ ] Configuration: `cloudbuild.yaml`

## 8. Deploy
- [ ] `git push` to main branch
- [ ] Monitor build at **Cloud Build > History**

---

## Environment Variables (set automatically by cloudbuild.yaml)

| Variable | Value |
|----------|-------|
| DB_USER | `tournament` |
| DB_NAME | `tournament_db` |
| DB_HOST | `/cloudsql/{PROJECT_ID}:us-central1:tournament-db` |
| DB_PASS | From Secret Manager: `tournament-db-pass` |
| SECRET_KEY | From Secret Manager: `flask-secret-key` |
| FLASK_ENV | `production` |
| GCP_PROJECT_ID | `{PROJECT_ID}` |
| GCP_REGION | `us-central1` |
