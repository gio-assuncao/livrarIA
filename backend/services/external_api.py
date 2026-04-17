import os
import logging
from typing import List, Optional
import httpx
from dotenv import load_dotenv
from schemas import ExternalSearchResult

load_dotenv()

logger = logging.getLogger(__name__)

GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"


class ExternalAPIService:
    """Fetches books from Google Books and Open Library."""

    async def search_google_books(self, query: str) -> List[ExternalSearchResult]:
        params = {"q": query, "maxResults": 10}
        if GOOGLE_BOOKS_API_KEY:
            params["key"] = GOOGLE_BOOKS_API_KEY

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(GOOGLE_BOOKS_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.warning(f"Google Books API error: {e}")
            return []

        results = []
        for item in data.get("items", []):
            info = item.get("volumeInfo", {})
            authors = info.get("authors", [])
            results.append(
                ExternalSearchResult(
                    external_id=item.get("id", ""),
                    source="google_books",
                    title=info.get("title", "Unknown Title"),
                    author=authors[0] if authors else None,
                    description=info.get("description"),
                    categories=info.get("categories", []),
                )
            )
        return results

    async def search_open_library(self, query: str) -> List[ExternalSearchResult]:
        params = {"q": query, "limit": 10, "fields": "key,title,author_name,first_sentence,subject"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(OPEN_LIBRARY_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            logger.warning(f"Open Library API error: {e}")
            return []

        results = []
        for doc in data.get("docs", []):
            author_names = doc.get("author_name", [])
            first_sentence = doc.get("first_sentence", [])
            description = first_sentence[0] if first_sentence else None
            subjects = doc.get("subject", [])[:5]

            results.append(
                ExternalSearchResult(
                    external_id=doc.get("key", ""),
                    source="open_library",
                    title=doc.get("title", "Unknown Title"),
                    author=author_names[0] if author_names else None,
                    description=description,
                    categories=subjects,
                )
            )
        return results

    async def search(self, query: str, source: str = "all") -> List[ExternalSearchResult]:
        """Dispatch search to one or both APIs, deduplicate by title+author."""
        results: List[ExternalSearchResult] = []

        if source in ("google_books", "all"):
            results.extend(await self.search_google_books(query))
        if source in ("open_library", "all"):
            results.extend(await self.search_open_library(query))

        # Deduplicate by normalized title+author
        seen = set()
        deduped = []
        for r in results:
            key = (r.title.lower().strip(), (r.author or "").lower().strip())
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        return deduped


external_api_service = ExternalAPIService()
