"""
Configuration module for LogAI.
"""

from .webhook_config import WebhookConfig, BranchConfig, default_config

__all__ = [
    "WebhookConfig",
    "BranchConfig", 
    "default_config"
]
