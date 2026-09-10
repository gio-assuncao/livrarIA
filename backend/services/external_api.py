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

    @staticmethod
    def _google_query(query: str, field: Optional[str]) -> str:
        if field == "author":
            return f'inauthor:"{query}"'
        if field == "subject":
            return f'subject:"{query}"'
        return query

    async def search_google_books(self, query: str, field: Optional[str] = None) -> List[ExternalSearchResult]:
        params = {"q": self._google_query(query, field), "maxResults": 10}
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
            thumbnail = info.get("imageLinks", {}).get("thumbnail")
            results.append(
                ExternalSearchResult(
                    external_id=item.get("id", ""),
                    source="google_books",
                    title=info.get("title", "Unknown Title"),
                    author=authors[0] if authors else None,
                    description=info.get("description"),
                    categories=info.get("categories", []),
                    cover_url=thumbnail.replace("http://", "https://") if thumbnail else None,
                )
            )
        return results

    async def search_open_library(self, query: str, field: Optional[str] = None) -> List[ExternalSearchResult]:
        params = {"limit": 10, "fields": "key,title,author_name,first_sentence,subject,cover_i"}
        if field == "author":
            params["author"] = query
        elif field == "subject":
            params["subject"] = query
        else:
            params["q"] = query

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
            cover_i = doc.get("cover_i")

            results.append(
                ExternalSearchResult(
                    external_id=doc.get("key", ""),
                    source="open_library",
                    title=doc.get("title", "Unknown Title"),
                    author=author_names[0] if author_names else None,
                    description=description,
                    categories=subjects,
                    cover_url=f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else None,
                )
            )
        return results

    async def search(
        self, query: str, source: str = "all", field: Optional[str] = None
    ) -> List[ExternalSearchResult]:
        """
        Dispatch search to one or both APIs (in parallel), deduplicate by title+author.
        `field` narrows the search: None (free text), "author" or "subject".
        """
        import asyncio

        tasks = []
        if source in ("google_books", "all"):
            tasks.append(self.search_google_books(query, field))
        if source in ("open_library", "all"):
            tasks.append(self.search_open_library(query, field))

        results: List[ExternalSearchResult] = []
        for batch in await asyncio.gather(*tasks):
            results.extend(batch)

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
