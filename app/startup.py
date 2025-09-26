"""
Startup script for Railway deployment.
This script is run when the web service starts, and contains the logic to
process the crawl and prioritization sequence.
"""
import asyncio
import os
import logging
from datetime import datetime
from app.scheduler import run_crawl_job
from fastapi import FastAPI
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

async def run_crawl_cron():
    """
    Internal cron job that runs every 40 minutes to trigger crawling.
    """
    logger.info("Starting internal crawl scheduler...")
    
    while True:
        try:
            logger.info(f"Running scheduled crawl at {datetime.now()}")
            count = await run_crawl_job(max_concurrent=3, domains=None)
            
            logger.info(f"Scheduled crawl completed. Upserted {count} items")
            
            await asyncio.sleep(2400)
        except Exception as e:
            logger.error(f"Error in scheduled crawl: {e}")
            await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("RAILWAY") and os.getenv("STARTUP_TASK") == "cron":
        logger.info("Starting internal crawl scheduler for Railway deployment")
        asyncio.create_task(run_crawl_cron())
    
    yield  # This is where the application runs
    
    logger.info("Application shutting down")


from app.main import app
app.router.lifespan_context = lifespan
