import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from database import Base, engine, SessionLocal
from routers import books, recommendations, external, chat
from services.embedding import embedding_service
from services.recommender import recommender_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Columns added after the first release. create_all() doesn't alter existing
# tables, so add them here idempotently to keep an old livrarIA.db working.
_NEW_COLUMNS = {
    "books": [("external_id", "VARCHAR"), ("cover_url", "VARCHAR")],
    "cache_books": [("created_at", "DATETIME"), ("cover_url", "VARCHAR")],
    "user_books": [("pasted_at", "DATETIME"), ("revealed_at", "DATETIME")],
}


def _apply_light_migrations():
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in _NEW_COLUMNS.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in existing:
                    logger.info(f"Migrating: adding {table}.{name}")
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        # Backfill invariants (idempotent): a pasted sticker was necessarily revealed.
        if "user_books" in insp.get_table_names():
            conn.execute(text(
                "UPDATE user_books SET revealed_at = pasted_at "
                "WHERE pasted_at IS NOT NULL AND revealed_at IS NULL"
            ))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    _apply_light_migrations()

    logger.info("Loading embedding model...")
    embedding_service.load_model()
    if embedding_service.dim:
        recommender_service.dim = embedding_service.dim

    logger.info("Building FAISS index...")
    db = SessionLocal()
    try:
        recommender_service.build_faiss_index(db)
    finally:
        db.close()

    logger.info("LivrarIA backend ready.")
    yield
    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("Shutting down.")


app = FastAPI(
    title="LivrarIA API",
    description="Local-first intelligent book recommendation system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(recommendations.router)
app.include_router(external.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "LivrarIA",
        "catalog_index_size": recommender_service.size,
    }
