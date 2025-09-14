# LogAI - Production Impact Detection System

Automate detection and simulation of production impact from PR merges using event triggers, code diff analysis, fine-tuned AI model predictions, and CI/CD gating.

## 🚀 Features

### ✅ Implemented: PR Detection and Triggering Workflow

- **GitHub & GitLab Integration**: Webhook-based PR merge detection
- **Branch Targeting**: Configurable main/staging branch monitoring
- **Event Processing**: Real-time PR merge event processing
- **Workflow Triggering**: Automated downstream workflow activation
- **Security**: HMAC signature verification for webhook authenticity
- **Monitoring**: Health checks and comprehensive logging

### 🔄 Coming Soon

- Code diff analysis
- AI model predictions
- Production impact simulation
- CI/CD gating mechanisms

## 📋 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd LogAI

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

### 3. Run the Server

```bash
# Start the webhook server
python main.py
```

### 4. Set Up Webhooks

Follow the detailed setup guide in [docs/WEBHOOK_SETUP.md](docs/WEBHOOK_SETUP.md) to configure webhooks in your Git providers.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub/GitLab │    │  LogAI Webhook   │    │  Your Workflow  │
│                 │    │     Server       │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │   Webhook   │─┼────┼→│ Event        │─┼────┼→│ Production  │ │
│ │   Events    │ │    │ │ Processing   │ │    │ │ Impact      │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ │ Analysis    │ │
└─────────────────┘    └──────────────────┘    │ └─────────────┘ │
                                               └─────────────────┘
```

## 📚 Documentation

- **[Webhook Setup Guide](docs/WEBHOOK_SETUP.md)** - Complete setup instructions
- **[API Reference](docs/API_REFERENCE.md)** - REST API documentation
- **[Configuration](docs/WEBHOOK_SETUP.md#configuration)** - Environment variables

## 🔧 Configuration

### Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_WEBHOOK_SECRET` | GitHub webhook verification secret | None |
| `GITLAB_WEBHOOK_SECRET` | GitLab webhook verification secret | None |
| `WORKFLOW_WEBHOOK_URL` | Your workflow trigger endpoint | None |
| `MAIN_BRANCHES` | Main branch names to monitor | `main,master` |
| `STAGING_BRANCHES` | Staging branch names to monitor | `staging,develop,dev` |

### Supported Branches

The system automatically detects PR merges to:
- **Main branches**: `main`, `master`
- **Staging branches**: `staging`, `develop`, `dev`

## 🎯 Supported Events

### GitHub Events
- **Pull Request**: Merged PRs targeting main/staging branches
- **Push**: Direct pushes to main/staging branches

### GitLab Events
- **Merge Request**: Merged MRs targeting main/staging branches
- **Push**: Direct pushes to main/staging branches

## 📊 Workflow Integration

When a PR is merged, the system sends a standardized payload to your workflow webhook:

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
  "risk_level": "medium"
}
```

## 🛡️ Security

- **HMAC-SHA256** signature verification for GitHub webhooks
- **Secret token** verification for GitLab webhooks
- **Environment-based** configuration management
- **HTTPS-ready** for production deployment

## 🚀 Production Deployment

### Docker

```bash
# Build image
docker build -t logai-webhook .

# Run container
docker run -p 8000:8000 --env-file .env logai-webhook
```

### Environment Setup

```bash
# Production environment variables
export GITHUB_WEBHOOK_SECRET="your-secure-secret"
export WORKFLOW_WEBHOOK_URL="https://your-workflow-endpoint.com/trigger"
export HOST="0.0.0.0"
export PORT="8000"
```

## 📈 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Logs

- Console output with structured JSON logging
- File logging with daily rotation (`logs/webhook_server.log`)

## 🧪 Testing

### Local Testing with ngrok

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from ngrok.com

# Run webhook server
python main.py

# Expose via ngrok
ngrok http 8000

# Use ngrok URL in your webhook configuration
```

### Manual Testing

```bash
# Test GitHub webhook
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d '{"action": "closed", "pull_request": {"merged": true}}'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Create an issue in the repository
- **Documentation**: Check the [docs/](docs/) directory
- **API Reference**: See [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

**Status**: MVP - PR Detection and Triggering Workflow ✅ Complete

Next: Code diff analysis and AI model integration