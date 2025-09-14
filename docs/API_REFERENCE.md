# API Reference

This document describes the REST API endpoints provided by the LogAI webhook server.

## Base URL

The API is available at the configured host and port (default: `http://localhost:8000`).

## Endpoints

### Health Check

#### GET /health

Check if the server is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-27T10:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Server is healthy

---

### GitHub Webhook

#### POST /webhooks/github

Receive GitHub webhook events for PR merges and pushes.

**Headers:**
- `X-GitHub-Event`: Event type (required)
- `X-GitHub-Delivery`: Unique delivery ID (required)
- `X-Hub-Signature-256`: HMAC signature for verification (optional)

**Supported Events:**
- `pull_request`: PR opened, closed, merged
- `push`: Direct pushes to branches

**Response:**
```json
{
  "status": "processed"
}
```

**Status Codes:**
- `200 OK`: Event processed successfully
- `401 Unauthorized`: Invalid signature
- `500 Internal Server Error`: Processing error

**Example Request:**
```bash
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: abc123-def456" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d '{
    "action": "closed",
    "pull_request": {
      "number": 123,
      "title": "Add feature",
      "merged": true,
      "base": {"ref": "main"},
      "user": {"login": "developer"}
    }
  }'
```

---

### GitLab Webhook

#### POST /webhooks/gitlab

Receive GitLab webhook events for MR merges and pushes.

**Headers:**
- `X-Gitlab-Event`: Event type (required)
- `X-Gitlab-Token`: Secret token for verification (optional)

**Supported Events:**
- `Merge Request Hook`: MR events
- `Push Hook`: Direct pushes to branches

**Response:**
```json
{
  "status": "processed"
}
```

**Status Codes:**
- `200 OK`: Event processed successfully
- `401 Unauthorized`: Invalid token
- `500 Internal Server Error`: Processing error

**Example Request:**
```bash
curl -X POST http://localhost:8000/webhooks/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Event: Merge Request Hook" \
  -H "X-Gitlab-Token: your-secret-token" \
  -d '{
    "object_attributes": {
      "action": "merge",
      "iid": 123,
      "title": "Add feature",
      "target_branch": "main"
    },
    "user": {"username": "developer"}
  }'
```

---

## Event Data Models

### PRMergeEvent

Standardized event data structure sent to workflow webhooks.

```json
{
  "event_type": "pr_merge",
  "provider": "github|gitlab",
  "repository": "owner/repo",
  "branch": "main",
  "pr_number": 123,
  "pr_title": "Add new feature",
  "pr_description": "Detailed description...",
  "author": "developer",
  "commit_sha": "abc123def456...",
  "merged_at": "2025-01-27T10:00:00Z",
  "base_branch": "main",
  "head_branch": "feature-branch",
  "files_changed": ["src/file1.py", "src/file2.py"],
  "additions": 150,
  "deletions": 25,
  "changed_files_count": 8,
  "processed_at": "2025-01-27T10:00:01Z",
  "event_id": "github_owner_repo_123_abc123",
  "branch_type": "main|staging|feature",
  "risk_level": "low|medium|high"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | string | Always "pr_merge" |
| `provider` | string | "github" or "gitlab" |
| `repository` | string | Full repository name (owner/repo) |
| `branch` | string | Target branch name |
| `pr_number` | integer | PR/MR number (0 for direct pushes) |
| `pr_title` | string | PR/MR title |
| `pr_description` | string | PR/MR description (optional) |
| `author` | string | Author username |
| `commit_sha` | string | Merge commit SHA |
| `merged_at` | string | ISO timestamp of merge |
| `base_branch` | string | Target branch |
| `head_branch` | string | Source branch |
| `files_changed` | array | List of changed files |
| `additions` | integer | Lines added |
| `deletions` | integer | Lines deleted |
| `changed_files_count` | integer | Number of files changed |
| `processed_at` | string | Processing timestamp |
| `event_id` | string | Unique event identifier |
| `branch_type` | string | "main", "staging", or "feature" |
| `risk_level` | string | Risk assessment ("low", "medium", "high") |

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message description"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `400 Bad Request` | Invalid request format |
| `401 Unauthorized` | Invalid webhook signature/token |
| `422 Unprocessable Entity` | Missing required fields |
| `500 Internal Server Error` | Server processing error |

---

## Configuration

### Environment Variables

The server behavior can be configured using environment variables:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GITHUB_WEBHOOK_SECRET` | string | None | Secret for GitHub webhook verification |
| `GITLAB_WEBHOOK_SECRET` | string | None | Secret for GitLab webhook verification |
| `HOST` | string | `0.0.0.0` | Server host |
| `PORT` | integer | `8000` | Server port |
| `LOG_LEVEL` | string | `INFO` | Logging level |
| `MAIN_BRANCHES` | string | `main,master` | Comma-separated main branch names |
| `STAGING_BRANCHES` | string | `staging,develop,dev` | Comma-separated staging branch names |
| `WORKFLOW_WEBHOOK_URL` | string | None | URL to trigger workflows |
| `WORKFLOW_TIMEOUT` | integer | `30` | Workflow trigger timeout (seconds) |

---

## Rate Limiting

Currently, the API does not implement rate limiting. In production, consider implementing rate limiting at the reverse proxy level.

## Authentication

Webhook endpoints use signature/token verification:

- **GitHub**: HMAC-SHA256 signature verification
- **GitLab**: Secret token verification

Health check endpoint requires no authentication.

## CORS

CORS is not explicitly configured. For web-based clients, configure CORS in your reverse proxy or add CORS middleware to FastAPI.

## WebSocket Support

The API does not currently support WebSocket connections. All communication is HTTP-based.

---

## Example Integration

### Python Client

```python
import httpx
import json

async def trigger_workflow(event_data):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/webhooks/github",
            json=event_data,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery"
            }
        )
        return response.json()
```

### JavaScript Client

```javascript
async function triggerWorkflow(eventData) {
  const response = await fetch('http://localhost:8000/webhooks/github', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-GitHub-Event': 'pull_request',
      'X-GitHub-Delivery': 'test-delivery'
    },
    body: JSON.stringify(eventData)
  });
  
  return await response.json();
}
```

### cURL Examples

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test GitHub webhook
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: test-123" \
  -d '{"action": "closed", "pull_request": {"merged": true}}'

# Test GitLab webhook
curl -X POST http://localhost:8000/webhooks/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Event: Merge Request Hook" \
  -d '{"object_attributes": {"action": "merge"}}'
```
