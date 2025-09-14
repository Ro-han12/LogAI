"""
Main entry point for the LogAI webhook server.
"""

import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from webhooks import create_app
from config import WebhookConfig


def main():
    """Main entry point."""
    # Load configuration
    config = WebhookConfig.from_env()
    
    # Create FastAPI app
    app = create_app(config)
    
    # Run server
    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    main()
