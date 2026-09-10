from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Book, CacheBook, UserBook
from schemas import BookStatus, ExternalSearchResult, UserBookRead
from services.catalog import cache_results
from services.external_api import external_api_service
from services.recommender import recommender_service

router = APIRouter(prefix="/api/external", tags=["external"])


@router.get("/search", response_model=List[ExternalSearchResult])
async def search_external(
    q: str = Query(..., min_length=1),
    source: Optional[str] = Query(default="all"),
    db: Session = Depends(get_db),
):
    """Search external APIs (Google Books, Open Library) and add results to the catalog."""
    results = await external_api_service.search(q, source or "all")
    await cache_results(db, results)
    return results


@router.post("/import/{external_id:path}", response_model=UserBookRead, status_code=201)
def import_book(
    external_id: str,
    source: str = Query(default="google_books"),
    status: BookStatus = Query(default="wishlist"),
    db: Session = Depends(get_db),
):
    """Import a catalog book into the user's library."""
    cache_entry = (
        db.query(CacheBook)
        .filter(CacheBook.external_id == external_id, CacheBook.source == source)
        .first()
    )
    if not cache_entry:
        raise HTTPException(status_code=404, detail="Cached book not found. Search first.")

    # Already in the library? Return the existing entry instead of duplicating.
    existing = (
        db.query(UserBook)
        .join(Book)
        .filter(Book.external_id == external_id, Book.source == source)
        .first()
    )
    if existing:
        return existing

    book = Book(
        title=cache_entry.title,
        author=cache_entry.author or "Autor desconhecido",
        description=cache_entry.description,
        categories=cache_entry.categories,
        cover_url=cache_entry.cover_url,
        embedding=cache_entry.embedding,
        source=cache_entry.source,
        external_id=cache_entry.external_id,
    )
    db.add(book)
    db.flush()

    user_book = UserBook(book_id=book.id, status=status)
    db.add(user_book)
    db.commit()
    db.refresh(user_book)

    # A library book is no longer a recommendation candidate.
    recommender_service.remove_from_index(cache_entry.id)

    return user_book
