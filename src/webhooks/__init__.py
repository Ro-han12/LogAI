"""
Webhook handling module for LogAI.

This module provides webhook server functionality for detecting
PR merges from GitHub and GitLab and triggering downstream workflows.
"""

from .webhook_server import WebhookServer, create_app
from .event_processor import EventProcessor, WorkflowTrigger

__all__ = [
    "WebhookServer",
    "create_app", 
    "EventProcessor",
    "WorkflowTrigger"
]
