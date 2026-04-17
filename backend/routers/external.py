from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import Book, CacheBook, UserBook
from schemas import ExternalSearchResult, UserBookRead
from services.embedding import embedding_service
from services.external_api import external_api_service
from services.recommender import recommender_service

router = APIRouter(prefix="/api/external", tags=["external"])


@router.get("/search", response_model=List[ExternalSearchResult])
async def search_external(
    q: str = Query(..., min_length=1),
    source: Optional[str] = Query(default="all"),
    db: Session = Depends(get_db),
):
    """Search external APIs (Google Books, Open Library) and cache results."""
    results = await external_api_service.search(q, source or "all")

    # Cache results + generate embeddings for new books
    for result in results:
        existing = (
            db.query(CacheBook)
            .filter(
                CacheBook.external_id == result.external_id,
                CacheBook.source == result.source,
            )
            .first()
        )
        if existing:
            continue

        text = embedding_service.build_text(
            result.title,
            result.author or "",
            result.description or "",
            result.categories,
        )
        emb = embedding_service.get_embedding(text)

        cache_entry = CacheBook(
            external_id=result.external_id,
            source=result.source,
            title=result.title,
            author=result.author,
            description=result.description,
            categories=result.categories,
            embedding=emb,
        )
        db.add(cache_entry)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # race condition — already inserted by parallel request

    return results


@router.post("/import/{external_id}", response_model=UserBookRead, status_code=201)
def import_book(
    external_id: str,
    source: str = Query(default="google_books"),
    status: str = Query(default="wishlist"),
    db: Session = Depends(get_db),
):
    """Import a cached external book into the user's library."""
    cache_entry = (
        db.query(CacheBook)
        .filter(CacheBook.external_id == external_id, CacheBook.source == source)
        .first()
    )
    if not cache_entry:
        raise HTTPException(status_code=404, detail="Cached book not found. Search first.")

    # Create permanent Book record
    book = Book(
        title=cache_entry.title,
        author=cache_entry.author or "Unknown",
        description=cache_entry.description,
        categories=cache_entry.categories,
        embedding=cache_entry.embedding,
        source=cache_entry.source,
    )
    db.add(book)
    db.flush()

    user_book = UserBook(book_id=book.id, status=status)
    db.add(user_book)
    db.commit()
    db.refresh(user_book)

    # Update FAISS index
    if cache_entry.embedding:
        recommender_service.add_to_index(book.id, cache_entry.embedding)

    return user_book
