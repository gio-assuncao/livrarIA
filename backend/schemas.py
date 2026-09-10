from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field

BookStatus = Literal["read", "reading", "wishlist"]


# ── Book schemas ──────────────────────────────────────────────────────────────

class BookBase(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    categories: List[str] = []
    cover_url: Optional[str] = None
    source: str = "manual"


class BookCreate(BookBase):
    pass


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    external_id: Optional[str] = None
    # embedding intentionally not exposed (384 floats per book would bloat every list response)


# ── UserBook schemas ──────────────────────────────────────────────────────────

class UserBookCreate(BaseModel):
    book_id: int
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    status: BookStatus = "wishlist"
    tags: List[str] = []
    review: Optional[str] = None


class UserBookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    rating: Optional[int]
    status: str
    tags: List[str]
    review: Optional[str]
    created_at: datetime
    book: BookRead


class UserBookUpdate(BaseModel):
    # UserBook fields
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    status: Optional[BookStatus] = None
    tags: Optional[List[str]] = None
    review: Optional[str] = None
    # Book fields (optional — only updated if provided)
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None


# ── Add Book (creates both Book + UserBook) ───────────────────────────────────

class AddBookRequest(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    categories: List[str] = []
    cover_url: Optional[str] = None
    source: str = "manual"
    status: BookStatus = "read"
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: List[str] = []
    review: Optional[str] = None


# ── Recommendation schemas ────────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    """A catalog (CacheBook) entry ranked for the user. Import it via /api/external/import/{external_id}."""
    id: int                      # CacheBook.id
    external_id: str
    title: str
    author: str
    description: Optional[str]
    categories: List[str]
    source: str
    cover_url: Optional[str] = None
    score: float                 # hybrid score
    semantic_score: float = 0.0  # cosine similarity to the user profile
    category_score: float = 0.0  # Jaccard overlap of canonical categories
    reason: str


class DiscoverResponse(BaseModel):
    queries: List[str]
    new_books: int
    catalog_size: int


# ── External search schemas ───────────────────────────────────────────────────

class ExternalSearchResult(BaseModel):
    external_id: str
    source: str
    title: str
    author: Optional[str]
    description: Optional[str]
    categories: List[str]
    cover_url: Optional[str] = None


# ── Chat schemas ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    tool_calls_made: List[str] = []
