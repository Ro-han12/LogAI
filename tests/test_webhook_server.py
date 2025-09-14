"""
Tests for the webhook server functionality.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.webhooks.webhook_server import create_app
from src.config.webhook_config import WebhookConfig


class TestWebhookServer:
    """Test cases for webhook server."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return WebhookConfig(
            github_secret="test-github-secret",
            gitlab_secret="test-gitlab-secret",
            workflow_webhook_url="http://test-workflow.com/trigger"
        )
    
    @pytest.fixture
    def client(self, config):
        """Test client."""
        app = create_app(config)
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_github_pr_merge_event(self, client):
        """Test GitHub PR merge event processing."""
        payload = {
            "action": "closed",
            "pull_request": {
                "number": 123,
                "title": "Test PR",
                "merged": True,
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
                "user": {"login": "testuser"},
                "merge_commit_sha": "abc123def456",
                "merged_at": "2025-01-27T10:00:00Z",
                "additions": 100,
                "deletions": 20,
                "changed_files": 5
            },
            "repository": {
                "full_name": "test/repo"
            }
        }
        
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-id"
        }
        
        with patch('src.webhooks.webhook_server.WebhookServer._trigger_workflow') as mock_trigger:
            mock_trigger.return_value = AsyncMock()
            
            response = client.post(
                "/webhooks/github",
                json=payload,
                headers=headers
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "processed"}
    
    def test_github_push_event(self, client):
        """Test GitHub push event processing."""
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "test/repo"
            },
            "pusher": {
                "name": "testuser"
            },
            "head_commit": {
                "id": "abc123def456"
            }
        }
        
        headers = {
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "test-delivery-id"
        }
        
        with patch('src.webhooks.webhook_server.WebhookServer._trigger_workflow') as mock_trigger:
            mock_trigger.return_value = AsyncMock()
            
            response = client.post(
                "/webhooks/github",
                json=payload,
                headers=headers
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "processed"}
    
    def test_gitlab_mr_merge_event(self, client):
        """Test GitLab MR merge event processing."""
        payload = {
            "object_attributes": {
                "action": "merge",
                "iid": 123,
                "title": "Test MR",
                "target_branch": "main",
                "source_branch": "feature-branch",
                "merge_commit_sha": "abc123def456",
                "updated_at": "2025-01-27T10:00:00Z"
            },
            "user": {
                "username": "testuser"
            },
            "project": {
                "path_with_namespace": "test/repo"
            }
        }
        
        headers = {
            "X-Gitlab-Event": "Merge Request Hook",
            "X-Gitlab-Token": "test-gitlab-secret"
        }
        
        with patch('src.webhooks.webhook_server.WebhookServer._trigger_workflow') as mock_trigger:
            mock_trigger.return_value = AsyncMock()
            
            response = client.post(
                "/webhooks/gitlab",
                json=payload,
                headers=headers
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "processed"}
    
    def test_gitlab_push_event(self, client):
        """Test GitLab push event processing."""
        payload = {
            "ref": "refs/heads/main",
            "project": {
                "path_with_namespace": "test/repo"
            },
            "user_username": "testuser",
            "checkout_sha": "abc123def456"
        }
        
        headers = {
            "X-Gitlab-Event": "Push Hook",
            "X-Gitlab-Token": "test-gitlab-secret"
        }
        
        with patch('src.webhooks.webhook_server.WebhookServer._trigger_workflow') as mock_trigger:
            mock_trigger.return_value = AsyncMock()
            
            response = client.post(
                "/webhooks/gitlab",
                json=payload,
                headers=headers
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "processed"}
    
    def test_github_invalid_signature(self, client):
        """Test GitHub webhook with invalid signature."""
        payload = {"test": "data"}
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-id",
            "X-Hub-Signature-256": "sha256=invalid-signature"
        }
        
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 401
    
    def test_gitlab_invalid_token(self, client):
        """Test GitLab webhook with invalid token."""
        payload = {"test": "data"}
        headers = {
            "X-Gitlab-Event": "Merge Request Hook",
            "X-Gitlab-Token": "invalid-token"
        }
        
        response = client.post(
            "/webhooks/gitlab",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 401
    
    def test_ignored_event_types(self, client):
        """Test that non-target events are ignored."""
        # Test GitHub issue event (should be ignored)
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Test issue"
            }
        }
        
        headers = {
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "test-delivery-id"
        }
        
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "processed"}
    
    def test_non_target_branch_ignored(self, client):
        """Test that non-target branches are ignored."""
        payload = {
            "action": "closed",
            "pull_request": {
                "number": 123,
                "title": "Test PR",
                "merged": True,
                "base": {"ref": "feature-branch"},  # Not a target branch
                "head": {"ref": "another-feature"},
                "user": {"login": "testuser"},
                "merge_commit_sha": "abc123def456",
                "merged_at": "2025-01-27T10:00:00Z"
            },
            "repository": {
                "full_name": "test/repo"
            }
        }
        
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-id"
        }
        
        with patch('src.webhooks.webhook_server.WebhookServer._trigger_workflow') as mock_trigger:
            response = client.post(
                "/webhooks/github",
                json=payload,
                headers=headers
            )
            
            assert response.status_code == 200
            # Should not trigger workflow for non-target branch
            mock_trigger.assert_not_called()


class TestEventProcessor:
    """Test cases for event processor."""
    
    @pytest.fixture
    def processor(self):
        """Test event processor."""
        from src.webhooks.event_processor import EventProcessor, WorkflowTrigger
        
        triggers = [
            WorkflowTrigger(url="http://test-workflow.com/trigger")
        ]
        return EventProcessor(triggers)
    
    @pytest.mark.asyncio
    async def test_process_pr_merge_event(self, processor):
        """Test PR merge event processing."""
        event_data = {
            "provider": "github",
            "repository": "test/repo",
            "branch": "main",
            "pr_number": 123,
            "commit_sha": "abc123def456",
            "merged_at": "2025-01-27T10:00:00Z",
            "pr_title": "Test PR",
            "author": "testuser",
            "additions": 100,
            "deletions": 20,
            "changed_files_count": 5
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = AsyncMock()
            mock_post.return_value = mock_response
            
            result = await processor.process_pr_merge_event(event_data)
            
            assert result is True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_event_data(self, processor):
        """Test processing with invalid event data."""
        event_data = {
            "provider": "github",
            # Missing required fields
        }
        
        result = await processor.process_pr_merge_event(event_data)
        
        assert result is False
    
    def test_branch_type_detection(self, processor):
        """Test branch type detection."""
        assert processor._determine_branch_type("main") == "main"
        assert processor._determine_branch_type("master") == "main"
        assert processor._determine_branch_type("staging") == "staging"
        assert processor._determine_branch_type("develop") == "staging"
        assert processor._determine_branch_type("feature-branch") == "feature"
    
    def test_risk_level_assessment(self, processor):
        """Test risk level assessment."""
        # High risk
        event_data = {
            "changed_files_count": 100,
            "additions": 2000,
            "deletions": 500
        }
        assert processor._assess_risk_level(event_data) == "high"
        
        # Medium risk
        event_data = {
            "changed_files_count": 30,
            "additions": 600,
            "deletions": 200
        }
        assert processor._assess_risk_level(event_data) == "medium"
        
        # Low risk
        event_data = {
            "changed_files_count": 5,
            "additions": 100,
            "deletions": 20
        }
        assert processor._assess_risk_level(event_data) == "low"


if __name__ == "__main__":
    pytest.main([__file__])
