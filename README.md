# LivrarIA

A local-first intelligent book recommendation system with an LLM-powered agent interface.

## Features

- Track books you read, rate and tag them
- Get personalized recommendations via hybrid semantic + category ranking
- Search books from Google Books and Open Library
- Chat with an AI librarian (Claude) that explains *why* it recommends each book
- Clean, dark-mode UI

## Architecture

```
backend/   FastAPI + SQLAlchemy + SQLite + sentence-transformers + FAISS
frontend/  React + Vite + Tailwind CSS + React Query
```

The LLM (Claude) acts only as an interface layer — it calls backend tools to retrieve ranked results, never recommends books directly from its own knowledge.

---

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
cp .env .env.local
# Edit .env and fill in:
#   ANTHROPIC_API_KEY=sk-ant-...
#   GOOGLE_BOOKS_API_KEY=...  (optional, works without it)
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env .env.local
# VITE_API_BASE_URL=http://localhost:8000  (default, change if needed)
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
- Embedding model (`all-MiniLM-L6-v2`, ~80MB) is downloaded to the HuggingFace cache

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
| GET | `/api/recommendations` | Hybrid-ranked recommendations |
| POST | `/api/chat` | Chat with LLM agent |
| GET | `/api/external/search?q=...` | Search Google Books / Open Library |
| POST | `/api/external/import/{id}` | Import cached book to library |

Interactive API docs: **http://localhost:8000/docs**

---

## How Recommendations Work

1. **User profile** — weighted average of embeddings of rated books (weight = rating 1–5)
2. **Candidates** — books in the catalog (from external search, stored locally)
3. **Hybrid score** — `semantic_similarity * 0.6 + category_overlap * 0.3 + freshness * 0.1`
4. **Claude explains** — the agent receives ranked results and explains WHY each book suits you

## Environment Variables

| File | Variable | Required | Description |
|------|----------|----------|-------------|
| `backend/.env` | `ANTHROPIC_API_KEY` | Yes (for chat) | Claude API key |
| `backend/.env` | `GOOGLE_BOOKS_API_KEY` | No | Google Books API key |
| `backend/.env` | `SQLITE_URL` | No | Defaults to `sqlite:///./livrarIA.db` |
| `backend/.env` | `EMBEDDING_MODEL` | No | Defaults to `all-MiniLM-L6-v2` |
| `frontend/.env` | `VITE_API_BASE_URL` | No | Defaults to `http://localhost:8000` |
