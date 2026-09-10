from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import UserBook
from schemas import DiscoverResponse, RecommendationItem
from services.catalog import cache_results
from services.external_api import external_api_service
from services.recommender import recommender_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _reading_history(db: Session):
    return db.query(UserBook).filter(UserBook.status.in_(["read", "reading"])).all()


@router.get("", response_model=List[RecommendationItem])
def get_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    genre: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return hybrid-ranked catalog books for the current user."""
    user_books = _reading_history(db)
    if not user_books:
        return []

    user_profile = recommender_service.compute_user_profile(user_books)
    if user_profile is None:
        return []

    return recommender_service.hybrid_rank(
        user_profile=user_profile,
        limit=limit,
        db=db,
        genre_filter=genre,
        liked=recommender_service.liked_categories(user_books),
    )


@router.post("/discover", response_model=DiscoverResponse)
async def discover(
    max_queries: int = Query(default=6, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """
    Grow the catalog automatically: search the external APIs for the user's
    most-read authors and categories, so recommendations don't depend on
    manual searches.
    """
    user_books = _reading_history(db)
    authors, categories = recommender_service.top_interests(user_books)

    plan = [("author", a) for a in authors] + [("subject", c) for c in categories]
    plan = plan[:max_queries]

    new_books = 0
    for field, term in plan:
        results = await external_api_service.search(term, "all", field=field)
        new_books += await cache_results(db, results)

    return DiscoverResponse(
        queries=[f"{field}:{term}" for field, term in plan],
        new_books=new_books,
        catalog_size=recommender_service.size,
    )
