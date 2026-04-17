from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import UserBook
from schemas import RecommendationItem
from services.recommender import recommender_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=List[RecommendationItem])
def get_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    genre: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return hybrid-ranked book recommendations for the current user."""
    user_books = (
        db.query(UserBook)
        .filter(UserBook.status.in_(["read", "reading"]))
        .all()
    )

    if not user_books:
        return []

    user_profile = recommender_service.compute_user_profile(user_books)
    if user_profile is None:
        return []

    library_ids = {ub.book_id for ub in db.query(UserBook).all()}

    return recommender_service.hybrid_rank(
        user_profile=user_profile,
        limit=limit,
        db=db,
        genre_filter=genre,
        library_book_ids=library_ids,
    )
