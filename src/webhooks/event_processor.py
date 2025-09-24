"""
Event processing and workflow triggering logic.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import httpx
from loguru import logger


@dataclass
class WorkflowTrigger:
    """Workflow trigger configuration."""
    url: str
    method: str = "POST"
    headers: Dict[str, str] = None
    timeout: int = 30
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {"Content-Type": "application/json"}


class EventProcessor:
    """Processes webhook events and triggers downstream workflows."""
    
    def __init__(self, workflow_triggers: List[WorkflowTrigger]):
        self.workflow_triggers = workflow_triggers
        self.processed_events = []
    
    async def process_pr_merge_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process a PR merge event and trigger workflows.
        
        Args:
            event_data: The PR merge event data
            
        Returns:
            bool: True if processing was successful
        """
        try:
            logger.info(f"Processing PR merge event for {event_data.get('repository')} "
                       f"PR #{event_data.get('pr_number')}")
            
            # Validate event data
            if not self._validate_event_data(event_data):
                logger.error("Invalid event data")
                return False
            
            # Enrich event data
            enriched_data = await self._enrich_event_data(event_data)
            
            # Store processed event
            self.processed_events.append({
                "timestamp": datetime.now().isoformat(),
                "event_data": enriched_data
            })
            
            # Trigger workflows
            success_count = 0
            for trigger in self.workflow_triggers:
                if await self._trigger_workflow(trigger, enriched_data):
                    success_count += 1
            
            logger.info(f"Successfully triggered {success_count}/{len(self.workflow_triggers)} workflows")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error processing PR merge event: {e}")
            return False
    
    def _validate_event_data(self, event_data: Dict[str, Any]) -> bool:
        """Validate required fields in event data."""
        required_fields = [
            "provider", "repository", "branch", "pr_number", 
            "commit_sha", "merged_at"
        ]
        
        for field in required_fields:
            if field not in event_data or event_data[field] is None:
                logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    async def _enrich_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich event data with additional information."""
        enriched = event_data.copy()
        
        # Add processing metadata
        enriched["processed_at"] = datetime.now().isoformat()
        enriched["event_id"] = self._generate_event_id(event_data)
        
        # Determine branch type
        enriched["branch_type"] = self._determine_branch_type(event_data.get("branch", ""))
        
        # Add risk assessment (placeholder for future AI integration)
        enriched["risk_level"] = self._assess_risk_level(event_data)
        
        return enriched
    
    def _generate_event_id(self, event_data: Dict[str, Any]) -> str:
        """Generate a unique event ID."""
        provider = event_data.get("provider", "")
        repo = event_data.get("repository", "")
        pr_number = event_data.get("pr_number", 0)
        commit_sha = event_data.get("commit_sha", "")[:8]
        
        return f"{provider}_{repo}_{pr_number}_{commit_sha}".replace("/", "_")
    
    def _determine_branch_type(self, branch: str) -> str:
        """Determine the type of branch (main, staging, feature)."""
        main_branches = ["main", "master"]
        staging_branches = ["staging", "develop", "dev"]
        
        if branch in main_branches:
            return "main"
        elif branch in staging_branches:
            return "staging"
        else:
            return "feature"
    
    def _assess_risk_level(self, event_data: Dict[str, Any]) -> str:
        """Assess the risk level of the PR merge (placeholder for AI integration)."""
        # Simple heuristic based on file changes
        changed_files = event_data.get("changed_files_count", 0)
        additions = event_data.get("additions", 0)
        deletions = event_data.get("deletions", 0)
        
        total_changes = additions + deletions
        
        if changed_files > 50 or total_changes > 1000:
            return "high"
        elif changed_files > 20 or total_changes > 500:
            return "medium"
        else:
            return "low"
    
    async def _trigger_workflow(self, trigger: WorkflowTrigger, event_data: Dict[str, Any]) -> bool:
        """Trigger a specific workflow."""
        try:
            logger.info(f"Triggering workflow: {trigger.url}")
            
            async with httpx.AsyncClient() as client:
                if (trigger.method or "POST").upper() == "POST":
                    response = await client.post(
                        trigger.url,
                        json=event_data,
                        headers=trigger.headers,
                        timeout=trigger.timeout,
                    )
                else:
                    response = await client.request(
                        method=trigger.method,
                        url=trigger.url,
                        json=event_data,
                        headers=trigger.headers,
                        timeout=trigger.timeout,
                    )
                
                response.raise_for_status()
                logger.info(f"Workflow triggered successfully: {response.status_code}")
                return True
                
        except httpx.TimeoutException:
            logger.error(f"Workflow trigger timeout: {trigger.url}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Workflow trigger HTTP error: {e.response.status_code} - {trigger.url}")
            return False
        except Exception as e:
            logger.error(f"Workflow trigger error: {e} - {trigger.url}")
            return False
    
    async def get_processed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of processed events."""
        return self.processed_events[-limit:]
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about processed events."""
        if not self.processed_events:
            return {"total_events": 0}
        
        # Count events by provider
        provider_counts = {}
        branch_type_counts = {}
        risk_level_counts = {}
        
        for event in self.processed_events:
            event_data = event["event_data"]
            
            provider = event_data.get("provider", "unknown")
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            
            branch_type = event_data.get("branch_type", "unknown")
            branch_type_counts[branch_type] = branch_type_counts.get(branch_type, 0) + 1
            
            risk_level = event_data.get("risk_level", "unknown")
            risk_level_counts[risk_level] = risk_level_counts.get(risk_level, 0) + 1
        
        return {
            "total_events": len(self.processed_events),
            "provider_counts": provider_counts,
            "branch_type_counts": branch_type_counts,
            "risk_level_counts": risk_level_counts,
            "last_processed": self.processed_events[-1]["timestamp"] if self.processed_events else None
        }
