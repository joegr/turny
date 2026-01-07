#!/bin/bash
set -e

# GCP Resource Provisioning Script for Tournament Platform (Monolith)
# Run each section individually as needed

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Set GCP_PROJECT_ID or configure default project"
    exit 1
fi

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# =============================================================================
# STEP 1: Enable Required APIs
# =============================================================================
echo "=== STEP 1: Enabling Required APIs ==="
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    compute.googleapis.com \
    --project=$PROJECT_ID

echo "✓ APIs enabled"
echo ""

# =============================================================================
# STEP 1.5: Create Artifact Registry Repository
# =============================================================================
echo "=== STEP 1.5: Creating Artifact Registry Repository ==="
if gcloud artifacts repositories describe turny \
    --project=$PROJECT_ID \
    --location=$REGION 2>/dev/null; then
    echo "✓ Repository 'turny' already exists"
else
    gcloud artifacts repositories create turny \
        --project=$PROJECT_ID \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker repository for Tournament Platform"
    
    echo "✓ Repository created"
fi
echo ""

# =============================================================================
# STEP 2: Create Cloud SQL PostgreSQL Instance
# =============================================================================
echo "=== STEP 2: Creating Cloud SQL PostgreSQL Instance ==="
echo "This will take 5-10 minutes..."

# Check if instance exists
if gcloud sql instances describe tournament-db --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Cloud SQL instance 'tournament-db' already exists"
else
    gcloud sql instances create tournament-db \
        --project=$PROJECT_ID \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=10GB \
        --root-password=tournament123 \
        --assign-ip
    
    echo "✓ Cloud SQL instance created"
fi

# Create database if not exists
if gcloud sql databases describe tournament_db --instance=tournament-db --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Database 'tournament_db' already exists"
else
    gcloud sql databases create tournament_db --instance=tournament-db --project=$PROJECT_ID
    echo "✓ Database 'tournament_db' created"
fi

# Create user if not exists
if gcloud sql users describe tournament --instance=tournament-db --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ User 'tournament' already exists"
else
    gcloud sql users create tournament \
        --instance=tournament-db \
        --project=$PROJECT_ID \
        --password=tournament123
    echo "✓ User 'tournament' created"
fi

# Create secret for DB password
echo "Creating secret for DB password..."
if gcloud secrets describe tournament-db-pass --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Secret 'tournament-db-pass' already exists"
else
    echo "⚠️  Creating tournament-db-pass secret with placeholder value."
    echo "   You MUST update this secret with your actual DB password:"
    echo "   gcloud secrets versions add tournament-db-pass --data-file=- --project=$PROJECT_ID"
    printf "CHANGE_ME" | gcloud secrets create tournament-db-pass --data-file=- --project=$PROJECT_ID
    echo "✓ Secret 'tournament-db-pass' created (UPDATE THE VALUE!)"
fi

# Create secret for Flask SECRET_KEY
echo "Creating secret for Flask SECRET_KEY..."
if gcloud secrets describe flask-secret-key --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Secret 'flask-secret-key' already exists"
else
    # Generate a random secret key
    FLASK_SECRET=$(openssl rand -hex 32)
    printf "$FLASK_SECRET" | gcloud secrets create flask-secret-key --data-file=- --project=$PROJECT_ID
    echo "✓ Secret 'flask-secret-key' created"
fi

CONNECTION_NAME=$(gcloud sql instances describe tournament-db --project=$PROJECT_ID --format="value(connectionName)")
echo "Connection Name: $CONNECTION_NAME"
echo ""

# =============================================================================
# STEP 3: Configure IAM Permissions
# =============================================================================
echo "=== STEP 3: Configure IAM Permissions ==="

# Create service account
SA_NAME="tournament-runner"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID 2>/dev/null; then
    echo "✓ Service account '$SA_NAME' already exists"
else
    gcloud iam service-accounts create $SA_NAME \
        --description="Service account for Tournament Platform" \
        --display-name="Tournament Runner" \
        --project=$PROJECT_ID
    echo "✓ Service account created"
fi

# Grant roles
echo "Granting roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudsql.client" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/artifactregistry.reader" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor" >/dev/null

# Grant Cloud Build service account access to secrets and Cloud SQL
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
CLOUDBUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

echo "Granting Cloud Build service account permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/secretmanager.secretAccessor" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/cloudsql.client" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/run.admin" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/iam.serviceAccountUser" >/dev/null

echo "✓ Roles granted"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo "=== Setup Complete ==="
echo ""
echo "Resources created:"
echo "1. Artifact Registry: turny"
echo "2. Cloud SQL: tournament-db (Connection: $CONNECTION_NAME)"
echo "3. Service Account: $SA_EMAIL"
echo "4. Secrets in Secret Manager:"
echo "   - tournament-db-pass (⚠️ UPDATE THIS with your actual DB password!)"
echo "   - flask-secret-key (auto-generated)"
echo ""
echo "IMPORTANT: Update the DB password secret before deploying:"
echo "  echo 'YOUR_ACTUAL_PASSWORD' | gcloud secrets versions add tournament-db-pass --data-file=- --project=$PROJECT_ID"
echo ""
echo "Then run: git push to trigger Cloud Build deployment."
