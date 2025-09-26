"""
Entry point for Hugging Face Spaces deployment.
This file sets up the FastAPI app with background scheduler and worker threads.
"""

import asyncio
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.main import app as main_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="News Crawler API",
    description="News crawler and summarization API deployed on Hugging Face Spaces",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/", main_app)


class PersistentScheduler:
    """
    Persistent scheduler for Hugging Face Spaces.
    Handles scheduled tasks with state persistence.
    """
    
    def __init__(self, crawl_interval: int = 2400, worker_interval: int = 300):
        self.crawl_interval = crawl_interval  # 40 minutes in seconds
        self.worker_interval = worker_interval  # 5 minutes in seconds
        self.last_crawl_run: Optional[datetime] = None
        self.last_worker_run: Optional[datetime] = None
        self.running = True
        
    def should_run_crawl(self) -> bool:
        """Check if crawl job should run."""
        if not self.last_crawl_run:
            return True
        return (datetime.now(timezone.utc) - self.last_crawl_run).total_seconds() >= self.crawl_interval
    
    def should_run_worker(self) -> bool:
        """Check if worker job should run."""
        if not self.last_worker_run:
            return True
        return (datetime.now(timezone.utc) - self.last_worker_run).total_seconds() >= self.worker_interval
    
    def mark_crawl_run(self):
        """Mark crawl job as run."""
        self.last_crawl_run = datetime.now(timezone.utc)
        logger.info("Crawl job marked as run at %s", self.last_crawl_run)
    
    def mark_worker_run(self):
        """Mark worker job as run."""
        self.last_worker_run = datetime.now(timezone.utc)
        logger.info("Worker job marked as run at %s", self.last_worker_run)
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Scheduler stopped")


scheduler = PersistentScheduler()


def run_scheduler():
    """
    Run the scheduler in a background thread.
    This function handles both crawl and worker jobs.
    """
    logger.info("Starting persistent scheduler thread...")
    
    while scheduler.running:
        try:
            if scheduler.should_run_crawl():
                logger.info("Running scheduled crawl job...")
                try:
                    from app.scheduler import run_crawl_job
                    
                    asyncio.run(run_crawl_job(max_concurrent=3))
                    scheduler.mark_crawl_run()
                    logger.info("Crawl job completed successfully")
                except Exception as e:
                    logger.error("Error running crawl job: %s", e)
            
            if scheduler.should_run_worker():
                logger.info("Running worker job...")
                try:
                    from app.workers.summarizer_worker import SummarizerWorker
                    
                    worker = SummarizerWorker(max_concurrent=1)
                    asyncio.run(worker.run_once())
                    scheduler.mark_worker_run()
                    logger.info("Worker job completed successfully")
                except Exception as e:
                    logger.error("Error running worker job: %s", e)
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error("Unexpected error in scheduler: %s", e)
            time.sleep(300)  # 5 minutes
    
    logger.info("Scheduler thread stopped")


scheduler_thread: Optional[threading.Thread] = None


@app.on_event("startup")
async def startup_event():
    """Start background threads when the app starts."""
    global scheduler_thread
    
    logger.info("Starting up Hugging Face Spaces application...")
    
    os.environ["HUGGINGFACE_SPACES"] = "true"
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler thread started")
    
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up when the app shuts down."""
    logger.info("Shutting down Hugging Face Spaces application...")
    
    if scheduler:
        scheduler.stop()
    
    if scheduler_thread and scheduler_thread.is_alive():
        scheduler_thread.join(timeout=5)
    
    logger.info("Application shutdown complete")


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "News Crawler API",
        "status": "running",
        "platform": "Hugging Face Spaces",
        "scheduler": {
            "running": scheduler.running,
            "last_crawl_run": scheduler.last_crawl_run.isoformat() if scheduler.last_crawl_run else None,
            "last_worker_run": scheduler.last_worker_run.isoformat() if scheduler.last_worker_run else None
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "time": datetime.now(timezone.utc).isoformat(),
        "platform": "Hugging Face Spaces"
    }

