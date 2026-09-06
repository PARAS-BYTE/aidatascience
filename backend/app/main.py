import os
import sys
import time

# Add project root to path so ml_engine is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.db.database import Base, engine, upgrade_sqlite_schema, SessionLocal
from app.services.auth_service import AuthService


def create_application() -> FastAPI:
    # Ensure database schema is ready
    Base.metadata.create_all(bind=engine)
    upgrade_sqlite_schema()

    # Ensure default user exists and orphan data is migrated
    with SessionLocal() as init_db:
        try:
            AuthService.ensure_default_user_and_migrate_orphans(init_db)
        except Exception as e:
            logger.warning(f"Default user migration error: {e}")

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    cors_origins = [o for o in settings.CORS_ORIGINS if o != "*"]
    has_wildcard = "*" in settings.CORS_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if not has_wildcard else [],
        allow_origin_regex=r".*" if has_wildcard else r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://.*\.vercel\.app$|^https://.*\.onrender\.com$|^https://.*\.hf\.space$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware for request logging & duration tracking
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"{request.method} {request.url.path} - Status: {response.status_code} - Duration: {process_time:.2f}ms"
            )
            return response
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            logger.error(f"Unhandled error handling request {request.url.path} ({process_time:.2f}ms): {str(exc)}", exc_info=True)
            origin = request.headers.get("origin") or "*"
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": str(exc),
                        "details": str(exc) if settings.ENVIRONMENT == "development" else None,
                    }
                },
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                },
            )

    # Global structured error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error handling request {request.url.path}: {str(exc)}", exc_info=True)
        origin = request.headers.get("origin") or "*"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(exc),
                    "details": str(exc) if settings.ENVIRONMENT == "development" else None,
                }
            },
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
        )

    # Mount API routers under prefix (e.g. /api/v1 and /api)
    app.include_router(api_router, prefix=settings.API_PREFIX)
    app.include_router(api_router, prefix="/api")

    # Serve production React frontend if built (dist directory exists)
    dist_dir = os.path.join(PROJECT_ROOT, "frontend", "dist")
    if os.path.isdir(dist_dir):
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        assets_dir = os.path.join(dist_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            file_path = os.path.join(dist_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(dist_dir, "index.html"))

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
