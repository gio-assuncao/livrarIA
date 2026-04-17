import axios from 'axios'
import type {
  UserBook,
  AddBookPayload,
  UserBookUpdate,
  RecommendationItem,
  ExternalSearchResult,
  ChatMessage,
  ChatResponse,
} from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// ── Books ──────────────────────────────────────────────────────────────────────

export const fetchUserBooks = (status?: string): Promise<UserBook[]> =>
  api.get('/api/books', { params: status ? { status } : {} }).then(r => r.data)

export const fetchUserBook = (id: number): Promise<UserBook> =>
  api.get(`/api/books/${id}`).then(r => r.data)

export const createBook = (data: AddBookPayload): Promise<UserBook> =>
  api.post('/api/books', data).then(r => r.data)

export const updateUserBook = (id: number, data: UserBookUpdate): Promise<UserBook> =>
  api.patch(`/api/books/${id}`, data).then(r => r.data)

export const deleteBook = (id: number): Promise<void> =>
  api.delete(`/api/books/${id}`).then(() => undefined)

// ── Recommendations ────────────────────────────────────────────────────────────

export const getRecommendations = (limit = 10, genre?: string): Promise<RecommendationItem[]> =>
  api.get('/api/recommendations', { params: { limit, ...(genre ? { genre } : {}) } }).then(r => r.data)

// ── External search ────────────────────────────────────────────────────────────

export const searchExternal = (q: string, source = 'all'): Promise<ExternalSearchResult[]> =>
  api.get('/api/external/search', { params: { q, source } }).then(r => r.data)

export const importBook = (externalId: string, source: string, status = 'wishlist'): Promise<UserBook> =>
  api
    .post(`/api/external/import/${encodeURIComponent(externalId)}`, null, {
      params: { source, status },
    })
    .then(r => r.data)

// ── Chat ───────────────────────────────────────────────────────────────────────

export const sendChatMessage = (messages: ChatMessage[]): Promise<ChatResponse> =>
  api.post('/api/chat', { messages }).then(r => r.data)
