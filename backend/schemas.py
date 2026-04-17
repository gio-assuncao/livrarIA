from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


# ── Book schemas ──────────────────────────────────────────────────────────────

class BookBase(BaseModel):
    title: str
    author: str
    description: Optional[str] = None
    categories: List[str] = []
    source: str = "manual"


class BookCreate(BookBase):
    pass


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    embedding: Optional[List[float]] = None


# ── UserBook schemas ──────────────────────────────────────────────────────────

class UserBookCreate(BaseModel):
    book_id: int
    rating: Optional[int] = None
    status: str = "wishlist"
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
    rating: Optional[int] = None
    status: Optional[str] = None
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
    source: str = "manual"
    status: str = "read"
    rating: Optional[int] = None
    tags: List[str] = []
    review: Optional[str] = None


# ── Recommendation schemas ────────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    id: int
    title: str
    author: str
    description: Optional[str]
    categories: List[str]
    source: str
    score: float
    reason: str


# ── External search schemas ───────────────────────────────────────────────────

class ExternalSearchResult(BaseModel):
    external_id: str
    source: str
    title: str
    author: Optional[str]
    description: Optional[str]
    categories: List[str]


# ── Chat schemas ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    tool_calls_made: List[str] = []
