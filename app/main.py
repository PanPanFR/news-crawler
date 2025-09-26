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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn.error")

try:
    from app.db.database import get_supabase_client, close_client  # type: ignore

    import os
    platform = os.getenv("PLATFORM", os.getenv("RAILWAY", "default"))
    
    if platform == "RAILWAY":
        from app.startup import lifespan
        app.router.lifespan_context = lifespan
    elif platform == "HUGGINGFACE_SPACES":
        @app.on_event("startup")
        async def _startup():
            try:
                await get_supabase_client()
                logger.info("Supabase client initialized for Hugging Face Spaces")
            except Exception as e:
                logger.info("Supabase client not initialized: %s", e)

        @app.on_event("shutdown")
        async def _shutdown():
            try:
                await close_client()
                logger.info("Supabase client closed for Hugging Face Spaces")
            except Exception:
                pass
    else:
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
except ImportError:
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

try:
    from app.api.routes import router as api_router  # type: ignore
    app.include_router(api_router, prefix="/api")
except Exception as e:
    logger.info("API router not loaded yet: %s", e)


@app.post("/trigger-crawl")
async def trigger_crawl_endpoint():
    """
    Endpoint that can be triggered by external services to start crawling.
    Works with Render, Hugging Face Spaces, and other platforms.
    """
    try:
        from app.scheduler import run_crawl_job
        count = await run_crawl_job(max_concurrent=3, domains=None)
        return {"status": "ok", "message": f"Triggered crawl job, upserted {count} items", "upserted": count}
    except Exception as e:
        logger.error(f"Error in trigger crawl endpoint: {e}")
        return {"status": "error", "message": str(e)}
