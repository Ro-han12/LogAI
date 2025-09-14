# Webhook Setup Guide

This guide explains how to set up and configure the LogAI webhook server for detecting PR merges from GitHub and GitLab.

## Overview

The webhook server automatically detects when pull requests are merged into target branches (main/staging) and triggers downstream workflows for production impact analysis.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Run the server:**
   ```bash
   python main.py
   ```

4. **Set up webhooks in your Git providers**

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_WEBHOOK_SECRET` | Secret for GitHub webhook verification | None |
| `GITLAB_WEBHOOK_SECRET` | Secret for GitLab webhook verification | None |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `MAIN_BRANCHES` | Comma-separated main branch names | `main,master` |
| `STAGING_BRANCHES` | Comma-separated staging branch names | `staging,develop,dev` |
| `WORKFLOW_WEBHOOK_URL` | URL to trigger downstream workflows | None |
| `WORKFLOW_TIMEOUT` | Timeout for workflow triggers (seconds) | `30` |

### Branch Configuration

The system monitors these branch types:
- **Main branches**: `main`, `master`
- **Staging branches**: `staging`, `develop`, `dev`

You can customize these in your `.env` file.

## GitHub Webhook Setup

### 1. Create a Webhook in GitHub

1. Go to your repository settings
2. Navigate to **Webhooks** → **Add webhook**
3. Configure:
   - **Payload URL**: `https://your-domain.com/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: Use the same value as `GITHUB_WEBHOOK_SECRET`
   - **Events**: Select "Pull requests" and "Pushes"
   - **Active**: ✓

### 2. Required Events

- **Pull request events**: Detects PR merges
- **Push events**: Detects direct pushes to main/staging branches

### 3. Webhook Payload Example

The server receives payloads like this:

```json
{
  "action": "closed",
  "pull_request": {
    "number": 123,
    "title": "Add new feature",
    "merged": true,
    "base": {"ref": "main"},
    "head": {"ref": "feature-branch"},
    "user": {"login": "developer"},
    "merge_commit_sha": "abc123...",
    "merged_at": "2025-01-27T10:00:00Z"
  },
  "repository": {
    "full_name": "owner/repo"
  }
}
```

## GitLab Webhook Setup

### 1. Create a Webhook in GitLab

1. Go to your project settings
2. Navigate to **Webhooks**
3. Configure:
   - **URL**: `https://your-domain.com/webhooks/gitlab`
   - **Secret token**: Use the same value as `GITLAB_WEBHOOK_SECRET`
   - **Triggers**: Select "Merge request events" and "Push events"
   - **SSL verification**: ✓

### 2. Required Events

- **Merge request events**: Detects MR merges
- **Push events**: Detects direct pushes to main/staging branches

### 3. Webhook Payload Example

The server receives payloads like this:

```json
{
  "object_attributes": {
    "action": "merge",
    "iid": 123,
    "title": "Add new feature",
    "target_branch": "main",
    "source_branch": "feature-branch",
    "merge_commit_sha": "abc123..."
  },
  "user": {
    "username": "developer"
  },
  "project": {
    "path_with_namespace": "owner/repo"
  }
}
```

## Workflow Integration

### Workflow Payload Format

When a PR is merged, the server sends this payload to your workflow webhook:

```json
{
  "event_type": "pr_merge",
  "provider": "github",
  "repository": "owner/repo",
  "branch": "main",
  "pr_number": 123,
  "pr_title": "Add new feature",
  "author": "developer",
  "commit_sha": "abc123...",
  "merged_at": "2025-01-27T10:00:00Z",
  "base_branch": "main",
  "head_branch": "feature-branch",
  "files_changed": [],
  "additions": 150,
  "deletions": 25,
  "changed_files_count": 8,
  "processed_at": "2025-01-27T10:00:01Z",
  "event_id": "github_owner_repo_123_abc123",
  "branch_type": "main",
  "risk_level": "medium"
}
```

### Setting Up Your Workflow Endpoint

Configure `WORKFLOW_WEBHOOK_URL` to point to your workflow trigger endpoint. The endpoint should:

1. Accept POST requests with JSON payload
2. Process the PR merge event data
3. Trigger your production impact analysis workflow
4. Return HTTP 200 on success

## Testing

### Local Testing with ngrok

1. Install ngrok: `brew install ngrok` (macOS) or download from ngrok.com
2. Run your webhook server: `python main.py`
3. Expose it via ngrok: `ngrok http 8000`
4. Use the ngrok URL in your webhook configuration
5. Test by creating and merging a PR

### Manual Testing

You can test the webhook endpoints directly:

```bash
# Test GitHub webhook
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: test-delivery-id" \
  -d @test_payload.json

# Test health endpoint
curl http://localhost:8000/health
```

## Security

### Webhook Verification

- **GitHub**: Uses HMAC-SHA256 signature verification
- **GitLab**: Uses secret token verification

Always set strong secrets in your environment variables.

### HTTPS

In production, always use HTTPS for webhook URLs. The webhook server should be deployed behind a reverse proxy with SSL termination.

## Monitoring

### Logs

Logs are written to:
- Console output (structured JSON)
- `logs/webhook_server.log` (rotated daily)

### Health Check

Monitor the health endpoint:
```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-27T10:00:00Z"
}
```

## Troubleshooting

### Common Issues

1. **Webhook not triggering**: Check webhook URL, secrets, and event selection
2. **Signature verification failed**: Verify secret matches between GitHub/GitLab and server
3. **Workflow not triggered**: Check `WORKFLOW_WEBHOOK_URL` and network connectivity
4. **Wrong branch detected**: Verify branch names in configuration

### Debug Mode

Set `LOG_LEVEL=DEBUG` in your `.env` file for detailed logging.

### Webhook Delivery Status

Check webhook delivery status in GitHub/GitLab webhook settings to see if requests are reaching your server.

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY main.py .

EXPOSE 8000
CMD ["python", "main.py"]
```

### Environment Variables

Set production environment variables:
- Strong webhook secrets
- Production workflow webhook URL
- Appropriate host/port for your deployment
- Production log level

### Reverse Proxy

Deploy behind nginx or similar:

```nginx
location /webhooks/ {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```
