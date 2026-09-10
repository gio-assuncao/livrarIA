# LivrarIA

A local-first intelligent book recommendation system with an LLM-powered agent interface.

## Features

- Track books you read, rate and tag them
- Get personalized recommendations via hybrid semantic + category ranking
- Search books from Google Books and Open Library
- Book covers fetched automatically from both sources
- Chat with an AI librarian (any OpenRouter model) that explains *why* it recommends each book
- Clean, dark-mode UI

## Architecture

```
backend/   FastAPI + SQLAlchemy + SQLite + sentence-transformers + FAISS
frontend/  React + Vite + Tailwind CSS + React Query
```

The LLM acts only as an interface layer — it calls backend tools to retrieve ranked results, never recommends books directly from its own knowledge.

---

## Requirements

- **Python 3.10+** and **Node 18+**
- ~500MB free disk: the embedding model (~470MB) is downloaded automatically on first backend start
- An [OpenRouter](https://openrouter.ai) API key — **only needed for the chat**; library, search and recommendations work without any key

## Setup

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in:
#   OPENROUTER_API_KEY=sk-or-...
#   LLM_MODEL=anthropic/claude-3.5-haiku   (any OpenRouter model id)
#   GOOGLE_BOOKS_API_KEY=...               (optional, works without it)

# Run the tests (offline, ~2s)
pip install pytest
pytest -q
```

### 2. Frontend

```bash
cd frontend
npm install
# .env → VITE_API_BASE_URL=http://localhost:8000  (must match the backend port below)
```

---

## Running

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate      # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

On first run:
- SQLite database is created (`livrarIA.db`)
- Embedding model (`paraphrase-multilingual-MiniLM-L12-v2`, ~470MB) is downloaded to the HuggingFace cache

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/books` | List user books (filter: `?status=read`) |
| POST | `/api/books` | Add book manually |
| PATCH | `/api/books/{id}` | Update rating/status/tags/review |
| DELETE | `/api/books/{id}` | Remove book |
| GET | `/api/recommendations` | Hybrid-ranked recommendations (`?limit=&genre=`) |
| POST | `/api/recommendations/discover` | Grow the catalog from your top authors/categories |
| POST | `/api/chat` | Chat with LLM agent |
| GET | `/api/external/search?q=...` | Search Google Books / Open Library |
| POST | `/api/external/import/{external_id}` | Import a catalog book to the library (`?source=&status=`) |

Interactive API docs: **http://localhost:8000/docs**

---

## How Recommendations Work

Two separate sets of books are involved:

- **Library** (`books` + `user_books`) — what you've read, are reading, or want to read. Read/reading books build your profile; nothing in the library is ever recommended back to you.
- **Catalog** (`cache_books`) — every book that ever came back from an external search (manual search on the Add page, the chat agent's `search_books`, or **Discover**). This is the candidate pool, and the FAISS index is built over it. Each entry stores the book's cover URL (Google Books `imageLinks`, Open Library covers API); entries cached before covers existed are backfilled the next time they appear in a search.

1. **User profile** — weighted average of the embeddings of read/reading books (weight = rating 1–5, unrated = 2)
2. **Candidates** — FAISS (`IndexIDMap` over `IndexFlatIP`) search over the catalog, over-fetching 5× `limit`; books already in the library (same `external_id` + `source`) are dropped
3. **Hybrid score** — `semantic_similarity * 0.6 + category_overlap * 0.3 + freshness * 0.1`
   - category overlap is Jaccard over *normalized* categories: `"Fiction / Thrillers / Suspense"`, `"Thrillers"` and `"Suspense"` all map to the same canonical tokens, bridging Google Books, Open Library and Portuguese labels
   - freshness decays over ~30 days from when the book entered the catalog
4. **The agent explains** — it receives ranked results and explains WHY each book suits you

If the catalog is empty, recommendations are empty. Use **Descobrir mais** on the dashboard (or `POST /api/recommendations/discover`) — it searches the external APIs for your most-read authors and categories and fills the catalog automatically.

Embeddings use `paraphrase-multilingual-MiniLM-L12-v2` (384 dims) so Portuguese titles, descriptions and categories embed well. Changing `EMBEDDING_MODEL` to a model with a different dimension requires deleting `livrarIA.db` (embeddings are stored per row).

## Environment Variables

| File | Variable | Required | Description |
|------|----------|----------|-------------|
| `backend/.env` | `OPENROUTER_API_KEY` | Yes (for chat) | OpenRouter API key |
| `backend/.env` | `LLM_MODEL` | No | OpenRouter model id, defaults to `anthropic/claude-3.5-haiku` |
| `backend/.env` | `GOOGLE_BOOKS_API_KEY` | No | Google Books API key |
| `backend/.env` | `SQLITE_URL` | No | Defaults to `sqlite:///./livrarIA.db` |
| `backend/.env` | `EMBEDDING_MODEL` | No | Defaults to `paraphrase-multilingual-MiniLM-L12-v2` |
| `frontend/.env` | `VITE_API_BASE_URL` | No | Defaults to `http://localhost:8000` |
