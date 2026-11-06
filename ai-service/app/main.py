"""
FastAPI AI Service Main Application Entrypoint.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.health import router as health_router
from app.api.rag import router as rag_router
from app.api.agent import router as agent_router
from app.core.config import settings
from app.mcp_server.transport import create_mcp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown."""
    print("=" * 60)
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Listening on: http://{settings.HOST}:{settings.PORT}")
    print("=" * 60)

    # Pre-warm local embedding model to eliminate cold-start latency on client queries
    try:
        from pathlib import Path
        from app.core.database import get_db
        from app.ingestion.embedder import LocalEmbeddingService
        print("  [Startup] Pre-warming HuggingFace embedding neural network...")
        LocalEmbeddingService.get_instance()
        print("  [Startup] Embedding model loaded and ready for inference.")

        # Ensure static company rules dataset is populated if store is unpopulated
        db = get_db()
        if db.get_total_chunks() == 0:
            docs_dir = Path(__file__).resolve().parents[2] / "company-docs"
            if docs_dir.exists():
                print(f"  [Startup] In-memory store unpopulated. Auto-indexing dataset from: {docs_dir}...")
                from app.ingestion.indexer import StaticDocIndexer
                indexer = StaticDocIndexer(db_manager=db)
                indexer.ingest_all_documents(docs_dir)
                print(f"  [Startup] Auto-indexed {db.get_total_chunks()} policy chunks into database.")
    except Exception as exc:
        print(f"  [Startup Warning] Initialization notice: {exc}")

    yield
    print(f"Shutting down {settings.PROJECT_NAME}")


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
    app.include_router(rag_router)
    app.include_router(agent_router)
    app.include_router(create_mcp_router())

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
