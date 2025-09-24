from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from datetime import datetime, timezone
import logging

__version__ = "0.1.0"

app = FastAPI(
    title="News Crawler Backend",
    version=__version__,
    default_response_class=ORJSONResponse,
)

# CORS configuration - adjust origins via env/config later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn.error")

# Initialize and close Supabase client with app lifecycle
try:
    from app.db.database import get_supabase_client, close_client  # type: ignore

    @app.on_event("startup")
    async def _startup():
        try:
            await get_supabase_client()
        except Exception as e:
            logger.info("Supabase client not initialized: %s", e)

    @app.on_event("shutdown")
    async def _shutdown():
        try:
            await close_client()
        except Exception:
            pass
except Exception as e:
    logger.info("Database module not available yet: %s", e)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "news-crawler-backend",
        "version": __version__,
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "time": datetime.now(timezone.utc).isoformat(),
    }

# Include API routers
try:
    from app.api.routes import router as api_router  # type: ignore
    app.include_router(api_router, prefix="/api")
except Exception as e:
    logger.info("API router not loaded yet: %s", e)


# Render cron job endpoint
@app.post("/trigger-crawl")
async def trigger_crawl_endpoint():
    """
    Endpoint that can be triggered by Render's cron job to start crawling.
    """
    try:
        from app.scheduler import run_crawl_job
        count = await run_crawl_job(max_concurrent=3, domains=None)
        return {"status": "ok", "message": f"Triggered crawl job, upserted {count} items", "upserted": count}
    except Exception as e:
        logger.error(f"Error in trigger crawl endpoint: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)