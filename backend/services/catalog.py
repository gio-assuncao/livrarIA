"""
Catalog service: turns external search results into CacheBook rows (with
embeddings) and keeps the FAISS index in sync. Shared by the /external
router, the /recommendations/discover endpoint and the chat agent.
"""
import logging
from typing import List, Set, Tuple

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError

from models import CacheBook
from schemas import ExternalSearchResult
from services.embedding import embedding_service
from services.recommender import recommender_service

logger = logging.getLogger(__name__)


async def cache_results(db, results: List[ExternalSearchResult]) -> int:
    """
    Persist external search results that are not yet in the catalog, generate
    their embeddings in one batch (off the event loop) and add them to the
    FAISS index. Returns the number of new catalog entries.
    """
    if not results:
        return 0

    keys: Set[Tuple[str, str]] = {(r.external_id, r.source) for r in results if r.external_id}
    if not keys:
        return 0

    by_key = {(r.external_id, r.source): r for r in results if r.external_id}
    existing: Set[Tuple[str, str]] = set()
    backfilled = False
    for row in (
        db.query(CacheBook)
        .filter(CacheBook.external_id.in_([k[0] for k in keys]))
        .all()
    ):
        existing.add((row.external_id, row.source))
        r = by_key.get((row.external_id, row.source))
        if r and r.cover_url and not row.cover_url:
            row.cover_url = r.cover_url  # cover added after the entry was cached
            backfilled = True
    if backfilled:
        db.commit()

    new_results, seen = [], set()
    for r in results:
        key = (r.external_id, r.source)
        if not r.external_id or key in existing or key in seen:
            continue
        seen.add(key)
        new_results.append(r)

    if not new_results:
        return 0

    texts = [
        embedding_service.build_text(r.title, r.author or "", r.description or "", r.categories)
        for r in new_results
    ]
    embeddings = await run_in_threadpool(embedding_service.get_embeddings_batch, texts)

    added: List[Tuple[int, List[float]]] = []
    for r, emb in zip(new_results, embeddings):
        entry = CacheBook(
            external_id=r.external_id,
            source=r.source,
            title=r.title,
            author=r.author,
            description=r.description,
            categories=r.categories,
            cover_url=r.cover_url,
            embedding=emb,
        )
        db.add(entry)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # inserted by a concurrent request — fine
            continue
        added.append((entry.id, emb))

    recommender_service.add_many_to_index(added)
    logger.info(f"Catalog: +{len(added)} books (index size {recommender_service.size}).")
    return len(added)
