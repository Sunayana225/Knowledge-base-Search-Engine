"""
Main entry point for the Knowledge-base Search Engine.
"""
import uvicorn
from src.config.settings import config


def main():
    """Run the application server."""
    uvicorn.run(
        "src.api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.debug
    )


if __name__ == "__main__":
    main()