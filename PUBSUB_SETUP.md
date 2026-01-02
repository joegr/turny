# Google Cloud Pub/Sub Setup Guide

## Overview

The tournament platform now uses **Google Cloud Pub/Sub** for real-time event streaming instead of polling. This provides:

- ✅ Real-time updates via Server-Sent Events (SSE)
- ✅ Scalable event distribution
- ✅ Reliable message delivery
- ✅ Perfect for Cloud Run serverless architecture

## Architecture

```
Tournament Event Flow:
┌─────────────────┐
│  Match Engine   │ ──> Publish events (team_registered, match_completed, etc.)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Pub/Sub Topic  │ ──> tournament-{tournament_id}
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Subscription   │ ──> tournament-{tournament_id}-sse-stream
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  SSE Endpoint   │ ──> /api/v1/play/{tournament_id}/events
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Frontend       │ ──> Real-time bracket updates
└─────────────────┘
```

## Event Types

The system publishes the following events:

1. **`team_registered`** - When a team joins a tournament
2. **`tournament_started`** - When a tournament begins
3. **`matches_created`** - When new matches are generated
4. **`match_completed`** - When a match result is recorded
5. **`round_advanced`** - When tournament advances to next round

## Local Development

In local development mode (`FLASK_ENV=development`), Pub/Sub is **simulated**:
- Events are logged but not actually published
- SSE endpoint returns empty stream
- Frontend falls back to polling if SSE fails

## GCP Setup

### 1. Enable Pub/Sub API

```bash
gcloud services enable pubsub.googleapis.com
```

### 2. Create Service Account with Pub/Sub Permissions

```bash
# Create service account
gcloud iam service-accounts create tournament-pubsub \
    --display-name="Tournament Pub/Sub Service Account"

# Grant Pub/Sub permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:tournament-pubsub@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:tournament-pubsub@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber"
```

### 3. Topics and Subscriptions

Topics and subscriptions are **automatically created** when tournaments start:

- **Topic**: `tournament-{tournament_id}`
- **Subscription**: `tournament-{tournament_id}-sse-stream`

The `PubSubManager` handles this automatically via:
- `ensure_topic_exists(tournament_id)`
- `ensure_subscription_exists(tournament_id, subscriber_id)`

### 4. Cloud Run Configuration

Update your Cloud Run service to use the Pub/Sub service account:

```bash
gcloud run services update tournament-app \
    --service-account=tournament-pubsub@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --region=us-central1
```

Or in `cloudbuild.yaml`:

```yaml
- name: 'gcr.io/cloud-builders/gcloud'
  args:
    - 'run'
    - 'deploy'
    - 'tournament-app'
    - '--service-account=tournament-pubsub@${PROJECT_ID}.iam.gserviceaccount.com'
```

## Environment Variables

Required environment variables for Cloud Run:

```bash
GCP_PROJECT_ID=your-project-id
FLASK_ENV=production
```

## Frontend Integration

### SSE Connection

The frontend automatically connects to the SSE endpoint:

```javascript
const eventSource = new EventSource(`/api/v1/play/${tournamentId}/events`);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Handle different event types
    if (data.event_type === 'match_completed') {
        // Update bracket visualization
        window.D3Bracket.render(tournamentId);
    }
};

eventSource.onerror = (error) => {
    // Fallback to polling if SSE fails
    console.error('SSE error:', error);
};
```

### Automatic Fallback

If SSE fails (e.g., in local development), the frontend automatically falls back to polling every 5 seconds.

## Cost Estimation

### Pub/Sub Pricing

- **First 10 GB/month**: Free
- **Beyond 10 GB**: $40 per TB

### Typical Tournament Usage

- **Events per tournament**: ~100-500 (registrations, matches, rounds)
- **Message size**: ~500 bytes average
- **Monthly cost for 1000 tournaments**: < $0.50

**Verdict**: Extremely cost-effective for tournament platform use case.

## Monitoring

### View Pub/Sub Metrics

```bash
# List all topics
gcloud pubsub topics list

# List subscriptions for a topic
gcloud pubsub topics list-subscriptions tournament-{tournament_id}

# View subscription metrics
gcloud pubsub subscriptions describe tournament-{tournament_id}-sse-stream
```

### Cloud Console

Monitor Pub/Sub in Cloud Console:
- Navigate to **Pub/Sub** → **Topics**
- View message throughput, delivery rates, and errors
- Set up alerts for failed deliveries

## Cleanup

### Delete Old Topics/Subscriptions

Topics and subscriptions are created per-tournament. To clean up old tournaments:

```bash
# List all tournament topics
gcloud pubsub topics list --filter="name:tournament-"

# Delete a specific topic (also deletes subscriptions)
gcloud pubsub topics delete tournament-{tournament_id}
```

Or use the API endpoint (to be implemented):

```bash
DELETE /api/v1/tournaments/{tournament_id}
# Should also clean up Pub/Sub resources
```

## Troubleshooting

### SSE Not Connecting

1. **Check service account permissions**:
   ```bash
   gcloud projects get-iam-policy YOUR_PROJECT_ID \
       --flatten="bindings[].members" \
       --filter="bindings.members:tournament-pubsub@*"
   ```

2. **Verify Pub/Sub API is enabled**:
   ```bash
   gcloud services list --enabled | grep pubsub
   ```

3. **Check Cloud Run logs**:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" --limit 50
   ```

### Messages Not Being Delivered

1. **Check subscription exists**:
   ```bash
   gcloud pubsub subscriptions describe tournament-{tournament_id}-sse-stream
   ```

2. **Check for undelivered messages**:
   ```bash
   gcloud pubsub subscriptions pull tournament-{tournament_id}-sse-stream --limit=10
   ```

3. **Verify topic has subscribers**:
   ```bash
   gcloud pubsub topics list-subscriptions tournament-{tournament_id}
   ```

## Security Best Practices

1. **Use service accounts** with minimal permissions (Publisher + Subscriber only)
2. **Enable VPC Service Controls** for additional security
3. **Set message retention** to 24 hours (already configured)
4. **Use IAM conditions** to restrict access by resource
5. **Monitor for anomalous activity** via Cloud Logging

## Next Steps

1. ✅ Pub/Sub integration complete
2. ✅ SSE endpoint implemented
3. ✅ Frontend updated with real-time updates
4. ✅ D3.js bracket visualization with live updates
5. 🔄 Deploy to Cloud Run and test
6. 🔄 Set up monitoring and alerts
7. 🔄 Implement cleanup job for old topics

## References

- [Google Cloud Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [Server-Sent Events (SSE) Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Cloud Run with Pub/Sub](https://cloud.google.com/run/docs/tutorials/pubsub)
