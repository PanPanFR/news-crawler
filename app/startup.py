"""
Startup script for Render deployment.
This script is run when the web service starts, and contains the logic to
process the crawl and prioritization sequence.
"""
import asyncio
import os
import logging
from app.scheduler import run_crawl_job, run_prioritizer
from fastapi import FastAPI
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Create a FastAPI app instance just for the lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup events
    if os.getenv("RENDER") and os.getenv("STARTUP_TASK") == "prioritizer":
        # When deployed on Render, run the prioritizer on startup
        # This will ensure the prioritizer runs after any crawl operations
        logger.info("Running prioritizer on startup for Render deployment")
        try:
            await run_prioritizer()
        except Exception as e:
            logger.error(f"Error running prioritizer on startup: {e}")
    
    yield  # This is where the application runs
    
    # Shutdown events
    logger.info("Application shutting down")


# Create the main app with the lifespan
from app.main import app
app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))