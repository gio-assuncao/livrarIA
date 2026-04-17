import { useState, useEffect } from 'react'
import { FiX, FiSave } from 'react-icons/fi'
import type { UserBook, UserBookUpdate } from '../types'

interface Props {
  userBook: UserBook
  onSave: (id: number, data: UserBookUpdate) => void
  onClose: () => void
  isSaving?: boolean
}

export default function EditBookModal({ userBook, onSave, onClose, isSaving }: Props) {
  const { book } = userBook

  const [title, setTitle] = useState(book.title)
  const [author, setAuthor] = useState(book.author)
  const [description, setDescription] = useState(book.description ?? '')
  const [categoriesInput, setCategoriesInput] = useState((book.categories ?? []).join(', '))
  const [tagsInput, setTagsInput] = useState((userBook.tags ?? []).join(', '))
  const [status, setStatus] = useState(userBook.status)
  const [rating, setRating] = useState<number | ''>(userBook.rating ?? '')
  const [review, setReview] = useState(userBook.review ?? '')

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(userBook.id, {
      title,
      author,
      description: description || undefined,
      categories: categoriesInput.split(',').map(s => s.trim()).filter(Boolean),
      tags: tagsInput.split(',').map(s => s.trim()).filter(Boolean),
      status,
      rating: rating !== '' ? Number(rating) : null,
      review: review || undefined,
    })
  }

  const inputCls = "w-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-600 focus:outline-none focus:border-violet-500"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl border border-neutral-200 dark:border-neutral-800 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-800">
          <h2 className="font-semibold text-neutral-900 dark:text-neutral-100">Editar Livro</h2>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 transition-colors p-1"
          >
            <FiX size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Título *</label>
              <input required value={title} onChange={e => setTitle(e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Autor *</label>
              <input required value={author} onChange={e => setAuthor(e.target.value)} className={inputCls} />
            </div>
          </div>

          <div>
            <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Descrição</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              className={`${inputCls} resize-none`}
              placeholder="Breve descrição..."
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Categorias (vírgula)</label>
              <input value={categoriesInput} onChange={e => setCategoriesInput(e.target.value)} className={inputCls} placeholder="Ficção, Terror" />
            </div>
            <div>
              <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Tags (vírgula)</label>
              <input value={tagsInput} onChange={e => setTagsInput(e.target.value)} className={inputCls} placeholder="sombrio, rápido" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Status</label>
              <select
                value={status}
                onChange={e => setStatus(e.target.value as typeof status)}
                className={inputCls}
              >
                <option value="read">Lido</option>
                <option value="reading">Lendo</option>
                <option value="wishlist">Lista de Desejos</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Avaliação (1–5)</label>
              <input
                type="number"
                min={1}
                max={5}
                value={rating}
                onChange={e => setRating(e.target.value === '' ? '' : Number(e.target.value))}
                className={inputCls}
                placeholder="1–5"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-neutral-500 dark:text-neutral-400 mb-1 block">Review</label>
            <textarea
              value={review}
              onChange={e => setReview(e.target.value)}
              rows={3}
              className={`${inputCls} resize-none`}
              placeholder="O que você achou do livro..."
            />
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 text-white text-sm font-medium transition-colors"
            >
              <FiSave size={14} />
              {isSaving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
