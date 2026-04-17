export interface Book {
  id: number
  title: string
  author: string
  description: string | null
  categories: string[]
  source: string
  embedding?: number[] | null
}

export interface UserBook {
  id: number
  book_id: number
  rating: number | null
  status: 'read' | 'reading' | 'wishlist'
  tags: string[]
  review: string | null
  created_at: string
  book: Book
}

export interface AddBookPayload {
  title: string
  author: string
  description?: string
  categories?: string[]
  source?: string
  status: 'read' | 'reading' | 'wishlist'
  rating?: number
  tags?: string[]
  review?: string
}

export interface UserBookUpdate {
  rating?: number | null
  status?: string
  tags?: string[]
  review?: string
  title?: string
  author?: string
  description?: string
  categories?: string[]
}

export interface RecommendationItem {
  id: number
  title: string
  author: string
  description: string | null
  categories: string[]
  source: string
  score: number
  reason: string
}

export interface ExternalSearchResult {
  external_id: string
  source: string
  title: string
  author: string | null
  description: string | null
  categories: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply: string
  tool_calls_made: string[]
}
