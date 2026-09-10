import logging
import re
import threading
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np

from schemas import RecommendationItem

logger = logging.getLogger(__name__)

# Score weights — see README "How Recommendations Work"
W_SEMANTIC = 0.6
W_CATEGORY = 0.3
W_FRESHNESS = 0.1


# ── Category normalization ─────────────────────────────────────────────────────
# Google Books returns things like "Fiction / Thrillers / Suspense", Open Library
# returns loose English subjects, and manual entries are usually in Portuguese.
# We split composite labels, strip accents, lowercase, and map common synonyms
# to a single canonical token so that Jaccard overlap and genre filters work
# across sources and languages.

_SYNONYMS: Dict[str, str] = {
    # EN -> canonical
    "fiction": "ficcao",
    "novel": "ficcao",
    "novels": "ficcao",
    "literary fiction": "ficcao",
    "thriller": "suspense",
    "thrillers": "suspense",
    "suspense": "suspense",
    "mystery": "misterio",
    "mystery & detective": "misterio",
    "detective": "misterio",
    "crime": "policial",
    "fantasy": "fantasia",
    "fantasy fiction": "fantasia",
    "science fiction": "ficcao cientifica",
    "sci-fi": "ficcao cientifica",
    "scifi": "ficcao cientifica",
    "horror": "terror",
    "horror fiction": "terror",
    "romance": "romance",
    "love stories": "romance",
    "historical fiction": "ficcao historica",
    "history": "historia",
    "biography": "biografia",
    "biography & autobiography": "biografia",
    "autobiography": "biografia",
    "memoir": "biografia",
    "self-help": "autoajuda",
    "self help": "autoajuda",
    "psychology": "psicologia",
    "philosophy": "filosofia",
    "poetry": "poesia",
    "juvenile fiction": "infantojuvenil",
    "young adult fiction": "jovem adulto",
    "young adult": "jovem adulto",
    "adventure": "aventura",
    "adventure stories": "aventura",
    "humor": "humor",
    "comics & graphic novels": "quadrinhos",
    "graphic novels": "quadrinhos",
    "comics": "quadrinhos",
    "business & economics": "negocios",
    "business": "negocios",
    "economics": "economia",
    "computers": "tecnologia",
    "technology": "tecnologia",
    "science": "ciencia",
    "religion": "religiao",
    "classics": "classicos",
    "short stories": "contos",
    "dystopian": "distopia",
    "dystopias": "distopia",
    # PT variants -> canonical
    "ficção": "ficcao",
    "ficcao": "ficcao",
    "romance policial": "policial",
    "policial": "policial",
    "mistério": "misterio",
    "misterio": "misterio",
    "fantasia": "fantasia",
    "ficção científica": "ficcao cientifica",
    "ficcao cientifica": "ficcao cientifica",
    "terror": "terror",
    "ficção histórica": "ficcao historica",
    "ficcao historica": "ficcao historica",
    "história": "historia",
    "historia": "historia",
    "biografia": "biografia",
    "autoajuda": "autoajuda",
    "auto-ajuda": "autoajuda",
    "psicologia": "psicologia",
    "filosofia": "filosofia",
    "poesia": "poesia",
    "infantojuvenil": "infantojuvenil",
    "infanto-juvenil": "infantojuvenil",
    "jovem adulto": "jovem adulto",
    "aventura": "aventura",
    "quadrinhos": "quadrinhos",
    "hq": "quadrinhos",
    "negócios": "negocios",
    "negocios": "negocios",
    "economia": "economia",
    "tecnologia": "tecnologia",
    "ciência": "ciencia",
    "ciencia": "ciencia",
    "religião": "religiao",
    "religiao": "religiao",
    "clássicos": "classicos",
    "classicos": "classicos",
    "contos": "contos",
    "distopia": "distopia",
}

_GENERIC = {"general", "geral", "misc", "miscellaneous", "outros", "other"}


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalize_category(label: str) -> Set[str]:
    """
    Turn one raw category label into a set of canonical tokens.
    "Fiction / Thrillers / Suspense" -> {"ficcao", "suspense"}
    "Ficção Científica"              -> {"ficcao cientifica"}
    """
    if not label:
        return set()
    out: Set[str] = set()
    for part in re.split(r"[/,;|>]+", label):
        raw = part.strip().lower()
        if not raw:
            continue
        canonical = _SYNONYMS.get(raw) or _SYNONYMS.get(_strip_accents(raw))
        if canonical is None:
            canonical = _strip_accents(raw)
        if canonical in _GENERIC:
            continue
        out.add(canonical)
    return out


def normalize_categories(labels: Optional[Iterable[str]]) -> Set[str]:
    out: Set[str] = set()
    for label in labels or []:
        out |= normalize_category(label)
    return out


# ── Recommender ────────────────────────────────────────────────────────────────

class RecommenderService:
    """
    Hybrid recommender: semantic (FAISS) + category overlap + freshness.

    Candidate pool = CacheBook (books discovered through external searches).
    User profile   = weighted average of Book embeddings the user has read / is reading.

    The FAISS index is an IndexIDMap over IndexFlatIP keyed by CacheBook.id, so
    entries can be added and removed individually without rebuilding.
    """

    def __init__(self, dim: int = 384):
        self.index = None
        self.dim = dim
        self._lock = threading.Lock()

    # ── Index lifecycle ────────────────────────────────────────────────────────

    def _new_index(self):
        import faiss
        return faiss.IndexIDMap(faiss.IndexFlatIP(self.dim))

    def build_faiss_index(self, db):
        """Load all CacheBook embeddings from DB and (re)build the index. Called at startup."""
        from models import CacheBook

        rows = (
            db.query(CacheBook.id, CacheBook.embedding)
            .filter(CacheBook.embedding.isnot(None))
            .all()
        )

        vectors, ids = [], []
        for cid, emb in rows:
            if emb and len(emb) == self.dim:
                vectors.append(emb)
                ids.append(cid)

        with self._lock:
            self.index = self._new_index()
            if vectors:
                self.index.add_with_ids(
                    np.asarray(vectors, dtype=np.float32),
                    np.asarray(ids, dtype=np.int64),
                )

        logger.info(f"FAISS index built with {len(ids)} catalog books.")

    def add_to_index(self, cache_book_id: int, embedding: List[float]):
        """Add (or replace) a single catalog book in the live index."""
        if self.index is None or not embedding or len(embedding) != self.dim:
            return
        with self._lock:
            self.index.remove_ids(np.asarray([cache_book_id], dtype=np.int64))
            self.index.add_with_ids(
                np.asarray([embedding], dtype=np.float32),
                np.asarray([cache_book_id], dtype=np.int64),
            )

    def add_many_to_index(self, items: List[Tuple[int, List[float]]]):
        items = [(i, e) for i, e in items if e and len(e) == self.dim]
        if self.index is None or not items:
            return
        ids = np.asarray([i for i, _ in items], dtype=np.int64)
        vecs = np.asarray([e for _, e in items], dtype=np.float32)
        with self._lock:
            self.index.remove_ids(ids)
            self.index.add_with_ids(vecs, ids)

    def remove_from_index(self, cache_book_id: int):
        if self.index is None:
            return
        with self._lock:
            self.index.remove_ids(np.asarray([cache_book_id], dtype=np.int64))

    @property
    def size(self) -> int:
        return int(self.index.ntotal) if self.index is not None else 0

    # ── User profile ───────────────────────────────────────────────────────────

    # Ratings are centered on RATING_NEUTRAL: above it a book attracts the
    # profile, below it the book *repels* (negative weight). Unrated reads
    # count as a mild positive — the user chose to read them.
    RATING_NEUTRAL = 2.5
    UNRATED_WEIGHT = 1.0

    def _signed_weight(self, rating: Optional[int]) -> float:
        return (float(rating) - self.RATING_NEUTRAL) if rating else self.UNRATED_WEIGHT

    def compute_user_profile(self, user_books) -> Optional[np.ndarray]:
        """
        Signed weighted average of read/reading book embeddings.
        Weight = rating - 2.5 (5* = +2.5 ... 1* = -1.5), unrated = +1.
        Low-rated books push the profile away from what the user disliked.
        Returns a normalized numpy vector, or None if no usable signal.
        """
        weighted_sum = np.zeros(self.dim, dtype=np.float32)
        total_weight = 0.0

        for ub in user_books:
            book = ub.book
            if not book or not book.embedding or len(book.embedding) != self.dim:
                continue
            weight = self._signed_weight(ub.rating)
            weighted_sum += weight * np.asarray(book.embedding, dtype=np.float32)
            total_weight += abs(weight)

        if total_weight == 0:
            return None

        profile = weighted_sum / total_weight
        norm = np.linalg.norm(profile)
        if norm < 1e-6:
            return None  # positive and negative signals cancelled out
        return profile / norm

    @staticmethod
    def liked_categories(user_books) -> Set[str]:
        """Canonical category tokens across books the user liked (rating >= 3 or unrated)."""
        cats: Set[str] = set()
        for ub in user_books:
            if ub.book and (ub.rating is None or ub.rating >= 3):
                cats |= normalize_categories(ub.book.categories)
        return cats

    def top_interests(self, user_books, n_authors: int = 3, n_categories: int = 3) -> Tuple[List[str], List[str]]:
        """Most frequent authors and raw categories among liked books — used by the discover step."""
        authors: Counter = Counter()
        cats: Counter = Counter()
        for ub in user_books:
            b = ub.book
            if not b:
                continue
            weight = self._signed_weight(ub.rating)
            if weight <= 0:
                continue  # don't grow the catalog toward books the user disliked
            if b.author and b.author.lower() != "unknown":
                authors[b.author] += weight
            for c in b.categories or []:
                for part in re.split(r"[/,;|>]+", c):
                    part = part.strip()
                    if part and part.lower() not in _GENERIC:
                        cats[part] += weight
        return (
            [a for a, _ in authors.most_common(n_authors)],
            [c for c, _ in cats.most_common(n_categories)],
        )

    # ── Feature scoring ────────────────────────────────────────────────────────

    @staticmethod
    def compute_feature_match(candidate_categories: Iterable[str], liked: Set[str]) -> float:
        """Jaccard similarity between canonical category sets."""
        cand = normalize_categories(candidate_categories)
        if not cand or not liked:
            return 0.0
        union = cand | liked
        return len(cand & liked) / len(union) if union else 0.0

    @staticmethod
    def compute_freshness(created_at: Optional[datetime]) -> float:
        """Books discovered more recently score higher. Decays over ~30 days."""
        if created_at is None:
            return 0.5
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        days = max(0.0, (now - created_at).total_seconds() / 86400.0)
        return 1.0 / (1.0 + days / 30.0)

    # ── Hybrid ranking ─────────────────────────────────────────────────────────

    def hybrid_rank(
        self,
        user_profile: np.ndarray,
        limit: int,
        db,
        genre_filter: Optional[str] = None,
        liked: Optional[Set[str]] = None,
    ) -> List[RecommendationItem]:
        """
        1. FAISS search over the catalog (over-fetch to survive filtering)
        2. Drop candidates already in the user's library (same external_id+source)
        3. Score: semantic*0.6 + category_overlap*0.3 + freshness*0.1
        4. Return top `limit`
        """
        from models import Book, CacheBook, UserBook

        if self.index is None or self.index.ntotal == 0:
            return []

        if liked is None:
            user_books = db.query(UserBook).filter(UserBook.status.in_(["read", "reading"])).all()
            liked = self.liked_categories(user_books)

        # Books already in the library, keyed by (external_id, source)
        in_library: Set[Tuple[str, str]] = {
            (ext, src)
            for ext, src in db.query(Book.external_id, Book.source).filter(Book.external_id.isnot(None))
        }

        genre_tokens = normalize_category(genre_filter) if genre_filter else set()
        genre_raw = _strip_accents(genre_filter.lower().strip()) if genre_filter else ""

        k = min(self.index.ntotal, max(limit * 5, 20))
        query = np.asarray([user_profile], dtype=np.float32)
        with self._lock:
            scores, ids = self.index.search(query, k)

        candidate_ids = [int(i) for i in ids[0] if i >= 0]
        sim_by_id = {int(i): float(s) for i, s in zip(ids[0], scores[0]) if i >= 0}
        if not candidate_ids:
            return []

        rows = db.query(CacheBook).filter(CacheBook.id.in_(candidate_ids)).all()
        by_id = {r.id: r for r in rows}

        results: List[RecommendationItem] = []
        for cid in candidate_ids:  # keep FAISS order for stable tie-breaks
            cb = by_id.get(cid)
            if not cb:
                continue
            if (cb.external_id, cb.source) in in_library:
                continue

            cand_tokens = normalize_categories(cb.categories)
            if genre_filter:
                raw_cats = " ".join(_strip_accents(c.lower()) for c in (cb.categories or []))
                if not (cand_tokens & genre_tokens) and genre_raw not in raw_cats:
                    continue

            sim = sim_by_id[cid]
            feature = self.compute_feature_match(cb.categories or [], liked)
            fresh = self.compute_freshness(cb.created_at)
            final = sim * W_SEMANTIC + feature * W_CATEGORY + fresh * W_FRESHNESS

            results.append(
                RecommendationItem(
                    id=cb.id,
                    external_id=cb.external_id,
                    title=cb.title,
                    author=cb.author or "Autor desconhecido",
                    description=cb.description,
                    categories=cb.categories or [],
                    source=cb.source,
                    cover_url=cb.cover_url,
                    score=round(float(final), 4),
                    semantic_score=round(sim, 4),
                    category_score=round(feature, 4),
                    reason=self._build_reason(sim, feature, cb.categories or []),
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    @staticmethod
    def _build_reason(sim: float, feature: float, categories: List[str]) -> str:
        pct = int(round(max(0.0, min(1.0, sim)) * 100))
        reason = f"Combina {pct}% com o seu perfil de leitura."
        top = [c for c in categories if c][:2]
        if top:
            reason += f" Categorias: {', '.join(top)}."
        if feature >= 0.34:
            reason += " Forte sobreposição de gêneros com livros que você gostou."
        elif feature > 0.1:
            reason += " Alguns gêneros em comum com o que você já leu."
        return reason


recommender_service = RecommenderService()
