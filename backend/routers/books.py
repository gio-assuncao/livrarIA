from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Book, UserBook
from schemas import AddBookRequest, BookRead, UserBookRead, UserBookUpdate
from services.embedding import embedding_service

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("", response_model=List[UserBookRead])
def list_user_books(status: Optional[str] = None, db: Session = Depends(get_db)):
    """List all user books, optionally filtered by status."""
    query = db.query(UserBook)
    if status:
        query = query.filter(UserBook.status == status)
    return query.order_by(UserBook.created_at.desc()).all()


@router.get("/{book_id}", response_model=UserBookRead)
def get_user_book(book_id: int, db: Session = Depends(get_db)):
    """Get a single user book by its UserBook ID."""
    ub = db.query(UserBook).filter(UserBook.id == book_id).first()
    if not ub:
        raise HTTPException(status_code=404, detail="Book not found")
    return ub


@router.post("", response_model=UserBookRead, status_code=201)
def add_book(payload: AddBookRequest, db: Session = Depends(get_db)):
    """Add a book manually to the library. Auto-generates embedding."""
    # Generate embedding
    text = embedding_service.build_text(
        payload.title, payload.author, payload.description or "", payload.categories
    )
    embedding = embedding_service.get_embedding(text)

    # Create Book record
    book = Book(
        title=payload.title,
        author=payload.author,
        description=payload.description,
        categories=payload.categories,
        cover_url=payload.cover_url,
        embedding=embedding,
        source=payload.source,
    )
    db.add(book)
    db.flush()  # get book.id without committing

    # Create UserBook record
    user_book = UserBook(
        book_id=book.id,
        rating=payload.rating,
        status=payload.status,
        tags=payload.tags,
        review=payload.review,
    )
    db.add(user_book)
    db.commit()
    db.refresh(user_book)

    return user_book


@router.patch("/{book_id}", response_model=UserBookRead)
def update_user_book(book_id: int, payload: UserBookUpdate, db: Session = Depends(get_db)):
    """Update rating, status, tags, review, and/or book metadata."""
    ub = db.query(UserBook).filter(UserBook.id == book_id).first()
    if not ub:
        raise HTTPException(status_code=404, detail="Book not found")

    # Update UserBook fields
    if payload.rating is not None:
        ub.rating = payload.rating
    if payload.status is not None:
        ub.status = payload.status
    if payload.tags is not None:
        ub.tags = payload.tags
    if payload.review is not None:
        ub.review = payload.review

    # Update Book fields if provided
    book = ub.book
    book_text_changed = False
    if payload.title is not None:
        book.title = payload.title
        book_text_changed = True
    if payload.author is not None:
        book.author = payload.author
        book_text_changed = True
    if payload.description is not None:
        book.description = payload.description
        book_text_changed = True
    if payload.categories is not None:
        book.categories = payload.categories
        book_text_changed = True

    # Regenerate embedding if text fields changed
    if book_text_changed:
        text = embedding_service.build_text(
            book.title, book.author, book.description or "", book.categories or []
        )
        book.embedding = embedding_service.get_embedding(text)

    db.commit()
    db.refresh(ub)
    return ub


@router.delete("/{book_id}", status_code=204)
def delete_user_book(book_id: int, db: Session = Depends(get_db)):
    """Delete a user book and its associated Book record."""
    ub = db.query(UserBook).filter(UserBook.id == book_id).first()
    if not ub:
        raise HTTPException(status_code=404, detail="Book not found")

    book_id_ref = ub.book_id
    db.delete(ub)
    db.flush()

    # Remove book if no other user_books reference it
    remaining = db.query(UserBook).filter(UserBook.book_id == book_id_ref).count()
    if remaining == 0:
        book = db.query(Book).filter(Book.id == book_id_ref).first()
        if book:
            db.delete(book)

    db.commit()
