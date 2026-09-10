import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Multilingual by default: the app is used in Portuguese, and the original
# all-MiniLM-L6-v2 is English-only (Portuguese descriptions embed poorly).
# Both models produce 384-dim vectors, so the FAISS index shape is unchanged.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")


class EmbeddingService:
    """Singleton wrapper around sentence-transformers. Loaded once at startup."""

    def __init__(self):
        self.model = None
        self.dim: Optional[int] = None

    def load_model(self):
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.dim = int(self.model.get_sentence_embedding_dimension())
        logger.info(f"Embedding model loaded ({self.dim} dims).")

    def _ensure_loaded(self):
        if self.model is None:
            self.load_model()

    def get_embedding(self, text: str) -> List[float]:
        """Encode a single text string. Returns a normalized float list."""
        self._ensure_loaded()
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch encode multiple texts."""
        if not texts:
            return []
        self._ensure_loaded()
        vectors = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vectors]

    @staticmethod
    def build_text(title: str, author: str, description: str = "", categories: Optional[list] = None) -> str:
        """Build a single text representation of a book for embedding."""
        cats = ", ".join(c for c in (categories or []) if c)
        parts = [title, author, description, cats]
        return ". ".join(p.strip() for p in parts if p and p.strip())


embedding_service = EmbeddingService()
