from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Book(Base):
    """A book that is in the user's library (referenced by at least one UserBook)."""

    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    categories = Column(JSON, default=list)  # list of strings
    embedding = Column(JSON, nullable=True)  # list of floats (384-dim)
    source = Column(String, default="manual")  # "manual", "google_books", "open_library"
    external_id = Column(String, nullable=True, index=True)  # id at the external source, if imported
    cover_url = Column(String, nullable=True)  # thumbnail URL from the external source

    user_books = relationship("UserBook", back_populates="book", cascade="all, delete-orphan")


class UserBook(Base):
    __tablename__ = "user_books"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5
    status = Column(String, nullable=False, default="wishlist")  # "read", "reading", "wishlist"
    tags = Column(JSON, default=list)  # list of strings
    review = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    book = relationship("Book", back_populates="user_books")


class CacheBook(Base):
    """
    Catalog of books discovered through external searches.
    This is the candidate pool for recommendations.
    """

    __tablename__ = "cache_books"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, nullable=False)
    source = Column(String, nullable=False)  # "google_books", "open_library"
    title = Column(String, nullable=False)
    author = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    categories = Column(JSON, default=list)
    cover_url = Column(String, nullable=True)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)  # drives the freshness score

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_external_source"),
    )
