import { useState, useCallback } from 'react'
import { sendChatMessage } from '../api/client'
import type { ChatMessage } from '../types'

const STORAGE_KEY = 'livraria_chat_history'

function loadHistory(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(messages: ChatMessage[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  } catch {
    // Storage full — ignore
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = { role: 'user', content: text }
    const updated = [...messages, userMsg]
    setMessages(updated)
    saveHistory(updated)
    setIsLoading(true)
    setError(null)

    try {
      const res = await sendChatMessage(updated)
      const assistantMsg: ChatMessage = { role: 'assistant', content: res.reply }
      const final = [...updated, assistantMsg]
      setMessages(final)
      saveHistory(final)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'An error occurred'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [messages])

  const clearChat = useCallback(() => {
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { messages, sendMessage, isLoading, error, clearChat }
}
