import logging
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np

from schemas import RecommendationItem

logger = logging.getLogger(__name__)


class RecommenderService:
    """Hybrid recommender: semantic (FAISS) + category overlap + freshness."""

    def __init__(self):
        self.index = None
        self.book_ids: List[int] = []
        self.dim = 384

    # ── Index lifecycle ────────────────────────────────────────────────────────

    def build_faiss_index(self, db):
        """Load all book embeddings from DB and build FAISS index. Called at startup."""
        import faiss
        from models import Book

        books = db.query(Book).filter(Book.embedding.isnot(None)).all()
        self.index = faiss.IndexFlatIP(self.dim)
        self.book_ids = []

        if not books:
            logger.info("FAISS index built (empty — no books with embeddings yet).")
            return

        vectors = []
        for book in books:
            if book.embedding and len(book.embedding) == self.dim:
                vectors.append(book.embedding)
                self.book_ids.append(book.id)

        if vectors:
            matrix = np.array(vectors, dtype=np.float32)
            self.index.add(matrix)

        logger.info(f"FAISS index built with {len(self.book_ids)} books.")

    def add_to_index(self, book_id: int, embedding: List[float]):
        """Incrementally add a single book to the live index (no rebuild needed)."""
        if self.index is None:
            return
        vector = np.array([embedding], dtype=np.float32)
        self.index.add(vector)
        self.book_ids.append(book_id)

    # ── User profile ───────────────────────────────────────────────────────────

    def compute_user_profile(self, user_books) -> Optional[np.ndarray]:
        """
        Weighted average of liked book embeddings.
        Weight = rating (1-5). Books being read without rating use weight=2.
        Returns a normalized numpy vector, or None if no data.
        """
        from models import Book
        weighted_sum = np.zeros(self.dim, dtype=np.float32)
        total_weight = 0.0

        for ub in user_books:
            book: Book = ub.book
            if not book or not book.embedding or len(book.embedding) != self.dim:
                continue
            weight = float(ub.rating) if ub.rating else 2.0
            weighted_sum += weight * np.array(book.embedding, dtype=np.float32)
            total_weight += weight

        if total_weight == 0:
            return None

        profile = weighted_sum / total_weight
        norm = np.linalg.norm(profile)
        if norm > 0:
            profile = profile / norm
        return profile

    # ── Feature matching ───────────────────────────────────────────────────────

    def compute_feature_match(self, candidate_categories: List[str], liked_categories: set) -> float:
        """Jaccard similarity between candidate's categories and liked books' categories."""
        if not candidate_categories or not liked_categories:
            return 0.0
        candidate_set = set(c.lower() for c in candidate_categories)
        intersection = candidate_set & liked_categories
        union = candidate_set | liked_categories
        return len(intersection) / len(union) if union else 0.0

    def compute_freshness(self, created_at: Optional[datetime]) -> float:
        """Books added more recently score higher. Decays over ~30 days."""
        if created_at is None:
            return 0.5
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        days = max(0, (now - created_at).days)
        return 1.0 / (1.0 + days / 30.0)

    # ── Hybrid ranking ─────────────────────────────────────────────────────────

    def hybrid_rank(
        self,
        user_profile: np.ndarray,
        limit: int,
        db,
        genre_filter: Optional[str] = None,
        library_book_ids: Optional[set] = None,
    ) -> List[RecommendationItem]:
        """
        1. FAISS search for top candidates (over-fetch by 3x)
        2. Filter already-in-library books
        3. Score: semantic*0.6 + feature_match*0.3 + freshness*0.1
        4. Return top `limit`
        """
        from models import Book, UserBook

        if self.index is None or self.index.ntotal == 0:
            return []

        # Collect user's liked books for feature matching
        user_books_all = (
            db.query(UserBook)
            .filter(UserBook.status.in_(["read", "reading"]))
            .all()
        )
        liked_categories: set = set()
        for ub in user_books_all:
            if ub.book and ub.book.categories:
                for cat in ub.book.categories:
                    liked_categories.add(cat.lower())

        if library_book_ids is None:
            library_book_ids = {ub.book_id for ub in db.query(UserBook).all()}

        # FAISS search
        k = min(self.index.ntotal, limit * 5)
        query = np.array([user_profile], dtype=np.float32)
        scores, indices = self.index.search(query, k)

        results: List[RecommendationItem] = []
        seen_ids = set()

        for idx, sim_score in zip(indices[0], scores[0]):
            if idx < 0 or idx >= len(self.book_ids):
                continue
            book_id = self.book_ids[idx]
            if book_id in library_book_ids or book_id in seen_ids:
                continue
            seen_ids.add(book_id)

            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                continue

            # Genre filter
            if genre_filter:
                cats_lower = [c.lower() for c in (book.categories or [])]
                if not any(genre_filter.lower() in c for c in cats_lower):
                    continue

            feature_score = self.compute_feature_match(book.categories or [], liked_categories)
            freshness_score = self.compute_freshness(None)  # CacheBooks have no created_at

            final_score = (float(sim_score) * 0.6) + (feature_score * 0.3) + (freshness_score * 0.1)

            # Build reason string
            top_cats = (book.categories or [])[:2]
            reason = (
                f"Matched {int(float(sim_score) * 100)}% semantically with your reading profile."
            )
            if top_cats:
                reason += f" Categories: {', '.join(top_cats)}."
            if feature_score > 0.1:
                reason += f" Strong category overlap with books you liked."

            results.append(
                RecommendationItem(
                    id=book.id,
                    title=book.title,
                    author=book.author,
                    description=book.description,
                    categories=book.categories or [],
                    source=book.source,
                    score=round(final_score, 4),
                    reason=reason,
                )
            )

            if len(results) >= limit * 2:
                break

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


recommender_service = RecommenderService()
