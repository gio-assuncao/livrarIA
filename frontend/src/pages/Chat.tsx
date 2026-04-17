import { useRef, useEffect, useState, type KeyboardEvent } from 'react'
import { FiSend, FiTrash2, FiZap } from 'react-icons/fi'
import { useChat } from '../hooks/useChat'
import ChatBubble, { TypingIndicator } from '../components/ChatBubble'

const SUGGESTIONS = [
  'Me recomende algo curto e perturbador',
  'Quero um livro de fantasia aconchegante',
  'O que ler se eu amei thrillers de ritmo acelerado?',
  'Mostre livros parecidos com o que já li',
]

export default function Chat() {
  const { messages, sendMessage, isLoading, error, clearChat } = useChat()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    await sendMessage(text)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Converse com a LivrarIA</h1>
          <p className="text-neutral-500 text-xs mt-0.5">
            Peça recomendações ou explore livros por tema, humor ou autor.
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-red-400 transition-colors px-2 py-1 rounded"
          >
            <FiTrash2 size={13} />
            Limpar
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <div className="w-12 h-12 rounded-full bg-violet-100 dark:bg-violet-900/40 border border-violet-300 dark:border-violet-800 flex items-center justify-center">
              <FiZap size={20} className="text-violet-400" />
            </div>
            <div>
              <p className="text-neutral-700 dark:text-neutral-300 font-medium mb-1">Sua bibliotecária pessoal</p>
              <p className="text-neutral-500 dark:text-neutral-600 text-sm max-w-xs">
                Pergunte qualquer coisa sobre livros. Vou pesquisar na sua biblioteca e recomendar pelo seu gosto.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-left text-xs text-neutral-500 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-900 hover:bg-neutral-200 dark:hover:bg-neutral-800 border border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 rounded-lg px-3 py-2.5 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}

        {error && (
          <div className="text-red-400 text-xs text-center py-2">
            Erro: {error}. Tente novamente.
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-4 flex gap-3 items-end">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={1}
          placeholder="Peça uma recomendação... (Enter para enviar, Shift+Enter para nova linha)"
          className="flex-1 bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 focus:border-violet-500 rounded-xl px-4 py-3 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-600 focus:outline-none resize-none disabled:opacity-50 leading-relaxed"
          style={{ minHeight: '48px', maxHeight: '160px' }}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="bg-violet-600 hover:bg-violet-500 disabled:bg-neutral-200 dark:disabled:bg-neutral-800 disabled:text-neutral-400 dark:disabled:text-neutral-600 text-white p-3 rounded-xl transition-colors shrink-0"
        >
          <FiSend size={16} />
        </button>
      </div>
    </div>
  )
}
