"""
Configuration management for webhook server.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BranchConfig(BaseModel):
    """Configuration for target branches."""
    main_branches: list[str] = Field(default=["main", "master"])
    staging_branches: list[str] = Field(default=["staging", "develop", "dev"])


class WebhookConfig(BaseModel):
    """Main webhook configuration."""
    
    # GitHub settings
    github_secret: Optional[str] = Field(default=None)
    github_webhook_url: str = Field(default="http://localhost:8000/webhooks/github")
    
    # GitLab settings
    gitlab_secret: Optional[str] = Field(default=None)
    gitlab_webhook_url: str = Field(default="http://localhost:8000/webhooks/gitlab")
    
    # Target branches
    target_branches: BranchConfig = Field(default_factory=BranchConfig)
    
    # Workflow settings
    workflow_webhook_url: Optional[str] = Field(default=None)
    workflow_timeout: int = Field(default=30)
    
    # Server settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    
    @classmethod
    def from_env(cls) -> "WebhookConfig":
        """Create configuration from environment variables."""
        return cls(
            github_secret=os.getenv("GITHUB_WEBHOOK_SECRET"),
            github_webhook_url=os.getenv("GITHUB_WEBHOOK_URL", "http://localhost:8000/webhooks/github"),
            gitlab_secret=os.getenv("GITLAB_WEBHOOK_SECRET"),
            gitlab_webhook_url=os.getenv("GITLAB_WEBHOOK_URL", "http://localhost:8000/webhooks/gitlab"),
            workflow_webhook_url=os.getenv("WORKFLOW_WEBHOOK_URL"),
            workflow_timeout=int(os.getenv("WORKFLOW_TIMEOUT", "30")),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            target_branches=BranchConfig(
                main_branches=os.getenv("MAIN_BRANCHES", "main,master").split(","),
                staging_branches=os.getenv("STAGING_BRANCHES", "staging,develop,dev").split(",")
            )
        )


# Default configuration instance
default_config = WebhookConfig.from_env()
