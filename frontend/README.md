# LivrarIA — Frontend

React + Vite + TypeScript + Tailwind CSS + React Query.

Setup, running instructions and API reference live in the [root README](../README.md).

## Quick start

```bash
npm install
npm run dev        # http://localhost:5173
```

The backend must be running (default `http://localhost:8000`); override with `VITE_API_BASE_URL` in `.env`.

## Structure

```
src/
  api/client.ts     All backend calls (axios instance)
  hooks/            React Query hooks (useBooks, useRecommendations, useChat, useTheme)
  pages/            Dashboard, AddBook, Wishlist, Chat
  components/       BookCard, BookGrid, EditBookModal, ChatBubble, NavBar, RatingStars, StatusBadge
  types/index.ts    API types mirrored from backend/schemas.py
```

When the backend schemas change, update `src/types/index.ts` to match.
