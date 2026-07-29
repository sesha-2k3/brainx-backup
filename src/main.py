# Main: FastAPI application entry point with lifespan management

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api import api_router
from src.config import get_settings
from src.db import close_db, init_db

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Frontend build directory
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Starting BrainX API...")

    # Initialize database tables (dev only - use migrations in production)
    if settings.is_development:
        await init_db()
        logger.info("Database initialized")

    yield

    # Cleanup
    await close_db()
    logger.info("BrainX API shutdown complete")


app = FastAPI(
    title="BrainX",
    description="BrainX - Personal Relationship Manager",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Serve frontend static files in production.
#
# Vite is configured with base: '/brainx/', so the built index.html references
# its bundles as /brainx/assets/*. This block previously mounted StaticFiles at
# /assets and served a catch-all from /, which meant every asset request fell
# through to the catch-all and received index.html - the browser got HTML where
# it expected JavaScript, and the app never booted when served by FastAPI.
# (The Vite dev server was unaffected, which is why this stayed hidden.)
FRONTEND_BASE = "/brainx"

if FRONTEND_DIR.exists():
    app.mount(
        f"{FRONTEND_BASE}/assets",
        StaticFiles(directory=FRONTEND_DIR / "assets"),
        name="assets",
    )

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        """Send bare / to the app's base path."""
        return RedirectResponse(url=f"{FRONTEND_BASE}/")

    @app.get(f"{FRONTEND_BASE}/{{full_path:path}}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve built files, falling back to index.html for client-side routes."""
        candidate = (FRONTEND_DIR / full_path).resolve()

        # Containment check: full_path is attacker-controlled, and without this
        # a traversal like ../../etc/passwd would be served happily.
        if candidate.is_file() and candidate.is_relative_to(FRONTEND_DIR.resolve()):
            return FileResponse(candidate)

        return FileResponse(FRONTEND_DIR / "index.html")
else:

    @app.get("/")
    async def root():
        """Root endpoint when frontend not built."""
        return {
            "name": "BrainX",
            "version": "0.1.0",
            "status": "running",
            "note": "Run 'npm run build' in frontend/ to enable web UI",
        }
