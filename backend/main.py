import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, SessionLocal
from routers import books, recommendations, external, chat
from services.embedding import embedding_service
from services.recommender import recommender_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("Loading embedding model...")
    embedding_service.load_model()

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
    return {"status": "ok", "service": "LivrarIA"}
