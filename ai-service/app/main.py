"""
FastAPI AI Service Main Application Entrypoint.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.health import router as health_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown."""
    print("=" * 60)
    print(f"🤖 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Listening on: http://{settings.HOST}:{settings.PORT}")
    print("=" * 60)
    yield
    print(f"🛑 Shutting down {settings.PROJECT_NAME}")


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI app instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Core AI engine powering Static PDF RAG, LangGraph workflows, and MCP integrations.",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(health_router)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "running",
            "docs": "/docs" if not settings.is_production else "disabled",
        }

    return app


app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.is_production,
    )
