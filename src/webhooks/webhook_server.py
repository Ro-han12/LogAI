"""
Webhook server for receiving GitHub and GitLab PR merge events.
Handles webhook verification, payload processing, and workflow triggering.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from pydantic import BaseModel, Field
import httpx
from loguru import logger

from utils import prepare_and_push_post_merge_branch


class ProviderType(str, Enum):
    """Supported webhook providers."""
    GITHUB = "github"
    GITLAB = "gitlab"


class BranchConfig(BaseModel):
    """Configuration for target branches."""
    main_branches: list[str] = ["main", "master"]
    staging_branches: list[str] = ["staging", "develop", "dev"]


class WebhookConfig(BaseModel):
    """Webhook configuration."""
    github_secret: Optional[str] = None
    gitlab_secret: Optional[str] = None
    target_branches: BranchConfig = Field(default_factory=BranchConfig)
    workflow_webhook_url: Optional[str] = None


class PRMergeEvent(BaseModel):
    """Standardized PR merge event data."""
    provider: ProviderType
    repository: str
    branch: str
    pr_number: int
    pr_title: str
    pr_description: Optional[str] = None
    author: str
    commit_sha: str
    merged_at: datetime
    base_branch: str
    head_branch: str
    files_changed: list[str] = []
    additions: int = 0
    deletions: int = 0
    changed_files_count: int = 0


class WebhookServer:
    """Main webhook server class."""
    
    def __init__(self, config: WebhookConfig):
        self.config = config
        self.app = FastAPI(title="LogAI Webhook Server", version="1.0.0")
        self._setup_routes()
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging."""
        logger.add(
            "logs/webhook_server.log",
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        @self.app.post("/webhooks/github")
        async def github_webhook(
            request: Request,
            x_github_event: str = Header(..., alias="X-GitHub-Event"),
            x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
            x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256")
        ):
            """Handle GitHub webhooks."""
            try:
                # Read raw body first for signature verification
                raw_body = await request.body()
                payload = await request.json()
                
                # Verify webhook signature if secret is configured
                if self.config.github_secret and x_hub_signature_256:
                    if not self._verify_github_signature_bytes(raw_body, x_hub_signature_256):
                        raise HTTPException(status_code=401, detail="Invalid signature")
                
                # Process the webhook event
                await self._process_github_event(x_github_event, payload, x_github_delivery)
                
                return {"status": "processed"}
                
            except HTTPException:
                # Let FastAPI handle intended HTTP errors
                raise
            except Exception as e:
                logger.error(f"Error processing GitHub webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/webhooks/gitlab")
        async def gitlab_webhook(
            request: Request,
            x_gitlab_event: str = Header(..., alias="X-Gitlab-Event"),
            x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token")
        ):
            """Handle GitLab webhooks."""
            try:
                payload = await request.json()
                
                # Verify webhook token if secret is configured
                if self.config.gitlab_secret and x_gitlab_token:
                    if x_gitlab_token != self.config.gitlab_secret:
                        raise HTTPException(status_code=401, detail="Invalid token")
                
                # Process the webhook event
                await self._process_gitlab_event(x_gitlab_event, payload)
                
                return {"status": "processed"}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing GitLab webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    def _verify_github_signature_bytes(self, body: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature from raw body bytes."""
        if not self.config.github_secret:
            return False
        expected_signature = "sha256=" + hmac.new(
            self.config.github_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    
    async def _process_github_event(self, event_type: str, payload: Dict[str, Any], delivery_id: str):
        """Process GitHub webhook events."""
        logger.info(f"Received GitHub event: {event_type}, delivery: {delivery_id}")
        
        if event_type == "pull_request":
            await self._handle_github_pr_event(payload)
        elif event_type == "push":
            await self._handle_github_push_event(payload)
        else:
            logger.info(f"Ignoring GitHub event type: {event_type}")
    
    async def _process_gitlab_event(self, event_type: str, payload: Dict[str, Any]):
        """Process GitLab webhook events."""
        logger.info(f"Received GitLab event: {event_type}")
        
        if event_type == "Merge Request Hook":
            await self._handle_gitlab_mr_event(payload)
        elif event_type == "Push Hook":
            await self._handle_gitlab_push_event(payload)
        else:
            logger.info(f"Ignoring GitLab event type: {event_type}")
    
    async def _handle_github_pr_event(self, payload: Dict[str, Any]):
        """Handle GitHub pull request events."""
        pr = payload.get("pull_request", {})
        action = payload.get("action", "")
        
        # Only process merged PRs
        if action != "closed" or not pr.get("merged"):
            logger.info(f"Ignoring GitHub PR event: action={action}, merged={pr.get('merged')}")
            return
        
        # Extract PR data
        pr_event = PRMergeEvent(
            provider=ProviderType.GITHUB,
            repository=payload.get("repository", {}).get("full_name", ""),
            branch=pr.get("base", {}).get("ref", ""),
            pr_number=pr.get("number", 0),
            pr_title=pr.get("title", ""),
            pr_description=pr.get("body"),
            author=pr.get("user", {}).get("login", ""),
            commit_sha=pr.get("merge_commit_sha", ""),
            merged_at=datetime.fromisoformat(pr.get("merged_at", "").replace("Z", "+00:00")),
            base_branch=pr.get("base", {}).get("ref", ""),
            head_branch=pr.get("head", {}).get("ref", ""),
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0),
            changed_files_count=pr.get("changed_files", 0)
        )
        
        # Check if target branch should trigger workflow
        if self._should_trigger_workflow(pr_event.branch):
            await self._trigger_workflow(pr_event)
    
    async def _handle_github_push_event(self, payload: Dict[str, Any]):
        """Handle GitHub push events (for direct pushes to main/staging)."""
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "")
        
        # Only process pushes to target branches
        if not self._should_trigger_workflow(branch):
            return
        
        # Create a synthetic PR event for direct pushes
        pr_event = PRMergeEvent(
            provider=ProviderType.GITHUB,
            repository=payload.get("repository", {}).get("full_name", ""),
            branch=branch,
            pr_number=0,  # Direct push
            pr_title=f"Direct push to {branch}",
            author=payload.get("pusher", {}).get("name", ""),
            commit_sha=payload.get("head_commit", {}).get("id", ""),
            merged_at=datetime.now(),
            base_branch=branch,
            head_branch=branch
        )
        
        await self._trigger_workflow(pr_event)
    
    async def _handle_gitlab_mr_event(self, payload: Dict[str, Any]):
        """Handle GitLab merge request events."""
        mr = payload.get("object_attributes", {})
        action = mr.get("action", "")
        
        # Only process merged MRs
        if action != "merge":
            logger.info(f"Ignoring GitLab MR event: action={action}")
            return
        
        # Extract MR data
        pr_event = PRMergeEvent(
            provider=ProviderType.GITLAB,
            repository=payload.get("project", {}).get("path_with_namespace", ""),
            branch=mr.get("target_branch", ""),
            pr_number=mr.get("iid", 0),
            pr_title=mr.get("title", ""),
            pr_description=mr.get("description"),
            author=payload.get("user", {}).get("username", ""),
            commit_sha=mr.get("merge_commit_sha", ""),
            merged_at=datetime.fromisoformat(mr.get("updated_at", "").replace("Z", "+00:00")),
            base_branch=mr.get("target_branch", ""),
            head_branch=mr.get("source_branch", "")
        )
        
        # Check if target branch should trigger workflow
        if self._should_trigger_workflow(pr_event.branch):
            await self._trigger_workflow(pr_event)
    
    async def _handle_gitlab_push_event(self, payload: Dict[str, Any]):
        """Handle GitLab push events."""
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "")
        
        # Only process pushes to target branches
        if not self._should_trigger_workflow(branch):
            return
        
        # Create a synthetic PR event for direct pushes
        pr_event = PRMergeEvent(
            provider=ProviderType.GITLAB,
            repository=payload.get("project", {}).get("path_with_namespace", ""),
            branch=branch,
            pr_number=0,  # Direct push
            pr_title=f"Direct push to {branch}",
            author=payload.get("user_username", ""),
            commit_sha=payload.get("checkout_sha", ""),
            merged_at=datetime.now(),
            base_branch=branch,
            head_branch=branch
        )
        
        await self._trigger_workflow(pr_event)
    
    def _should_trigger_workflow(self, branch: str) -> bool:
        """Check if the branch should trigger a workflow."""
        target_branches = (
            self.config.target_branches.main_branches + 
            self.config.target_branches.staging_branches
        )
        return branch in target_branches
    
    async def _trigger_workflow(self, pr_event: PRMergeEvent):
        """Trigger the downstream workflow."""
        logger.info(f"Triggering workflow for {pr_event.provider} PR #{pr_event.pr_number} "
                   f"merged to {pr_event.branch}")
        
        # Prepare workflow payload
        workflow_payload = {
            "event_type": "pr_merge",
            "provider": pr_event.provider,
            "repository": pr_event.repository,
            "branch": pr_event.branch,
            "pr_number": pr_event.pr_number,
            "pr_title": pr_event.pr_title,
            "author": pr_event.author,
            "commit_sha": pr_event.commit_sha,
            "merged_at": pr_event.merged_at.isoformat(),
            "base_branch": pr_event.base_branch,
            "head_branch": pr_event.head_branch,
            "files_changed": pr_event.files_changed,
            "additions": pr_event.additions,
            "deletions": pr_event.deletions,
            "changed_files_count": pr_event.changed_files_count
        }
        
        # Auto-create post-merge branch if configured
        if self.config.auto_create_post_merge_branch and self.config.post_merge_repo_path:
            await self._create_post_merge_branch(pr_event)
        
        # Send to workflow webhook if configured
        if self.config.workflow_webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.config.workflow_webhook_url,
                        json=workflow_payload,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    logger.info(f"Successfully triggered workflow: {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to trigger workflow: {e}")
        else:
            logger.info("No workflow webhook URL configured, logging event only")
            logger.info(f"Workflow payload: {json.dumps(workflow_payload, indent=2)}")
    
    async def _create_post_merge_branch(self, pr_event: PRMergeEvent):
        """Create and push a post-merge branch representing the merged state."""
        try:
            logger.info(f"Creating post-merge branch for PR #{pr_event.pr_number}")
            
            # Generate branch name
            branch_name = f"{self.config.post_merge_branch_prefix}/pr-{pr_event.pr_number}"
            
            # Determine source ref (use head_branch if available, otherwise commit_sha)
            source_ref = pr_event.head_branch if pr_event.head_branch else pr_event.commit_sha
            
            # Create and push the post-merge branch
            result = prepare_and_push_post_merge_branch(
                repository_path=self.config.post_merge_repo_path,
                base_branch=pr_event.branch,
                new_branch=branch_name,
                source_ref=f"{self.config.post_merge_remote_name}/{source_ref}",
                remote_name=self.config.post_merge_remote_name,
                push_force=False,
                commit_message=f"Post-merge state for PR #{pr_event.pr_number}: {pr_event.pr_title}"
            )
            
            logger.info(f"Successfully created post-merge branch: {result.remote_ref}")
            
        except Exception as e:
            logger.error(f"Failed to create post-merge branch: {e}")


def create_app(config: Optional[WebhookConfig] = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = WebhookConfig()
    
    server = WebhookServer(config)
    return server.app


if __name__ == "__main__":
    import uvicorn
    
    # Load configuration from environment
    config = WebhookConfig(
        github_secret=os.getenv("GITHUB_WEBHOOK_SECRET"),
        gitlab_secret=os.getenv("GITLAB_WEBHOOK_SECRET"),
        workflow_webhook_url=os.getenv("WORKFLOW_WEBHOOK_URL")
    )
    
    app = create_app(config)
    uvicorn.run(app, host="0.0.0.0", port=8000)
