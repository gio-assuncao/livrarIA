import os
import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


class EmbeddingService:
    """Singleton wrapper around sentence-transformers. Loaded once at startup."""

    def __init__(self):
        self.model = None

    def load_model(self):
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded.")

    def _ensure_loaded(self):
        if self.model is None:
            self.load_model()

    def get_embedding(self, text: str) -> List[float]:
        """Encode a single text string. Returns a normalized 384-dim float list."""
        self._ensure_loaded()
        import numpy as np
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch encode multiple texts."""
        self._ensure_loaded()
        vectors = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vectors]

    @staticmethod
    def build_text(title: str, author: str, description: str = "", categories: list = None) -> str:
        """Build a single text representation of a book for embedding."""
        cats = " ".join(categories or [])
        parts = filter(None, [title, author, description, cats])
        return " ".join(parts)


embedding_service = EmbeddingService()
