import { FiTrash2, FiEdit2 } from 'react-icons/fi'
import type { UserBook } from '../types'
import RatingStars from './RatingStars'
import StatusBadge from './StatusBadge'

interface Props {
  userBook: UserBook
  onRate?: (id: number, rating: number) => void
  onStatusChange?: (id: number, status: string) => void
  onDelete?: (id: number) => void
  onEdit?: (userBook: UserBook) => void
  score?: number
  reason?: string
}

export default function BookCard({ userBook, onRate, onStatusChange, onDelete, onEdit, score, reason }: Props) {
  const { book } = userBook

  return (
    <div className="flex flex-col gap-3 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-neutral-900 dark:text-neutral-100 truncate text-sm leading-tight">
            {book.title}
          </h3>
          <p className="text-neutral-500 dark:text-neutral-400 text-xs mt-0.5 truncate">{book.author}</p>
        </div>
        <div className="flex gap-1 shrink-0">
          {onEdit && (
            <button
              onClick={() => onEdit(userBook)}
              className="text-neutral-400 dark:text-neutral-600 hover:text-violet-600 dark:hover:text-violet-400 transition-colors p-0.5"
              aria-label="Editar livro"
            >
              <FiEdit2 size={13} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(userBook.id)}
              className="text-neutral-400 dark:text-neutral-600 hover:text-red-500 dark:hover:text-red-400 transition-colors p-0.5"
              aria-label="Remover livro"
            >
              <FiTrash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Score badge (recommendations) */}
      {score !== undefined && (
        <span className="self-start text-xs bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 border border-violet-300 dark:border-violet-800 px-2 py-0.5 rounded font-mono">
          {(score * 100).toFixed(0)}% compatível
        </span>
      )}

      {/* Description */}
      {book.description && (
        <p className="text-neutral-500 dark:text-neutral-500 text-xs line-clamp-2 leading-relaxed">
          {book.description}
        </p>
      )}

      {/* Reason (recommendations) */}
      {reason && (
        <p className="text-violet-600/70 dark:text-violet-400/70 text-xs italic leading-relaxed">{reason}</p>
      )}

      {/* Categories */}
      {book.categories.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {book.categories.slice(0, 3).map(cat => (
            <span
              key={cat}
              className="text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 px-2 py-0.5 rounded-full"
            >
              {cat}
            </span>
          ))}
        </div>
      )}

      {/* User tags */}
      {userBook.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {userBook.tags.map(tag => (
            <span
              key={tag}
              className="text-xs bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 px-2 py-0.5 rounded-full"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer: status + rating */}
      <div className="flex items-center justify-between pt-1">
        <StatusBadge status={userBook.status} />
        <RatingStars
          rating={userBook.rating}
          onRate={onRate ? (n) => onRate(userBook.id, n) : undefined}
        />
      </div>

      {/* Status quick-change */}
      {onStatusChange && (
        <div className="flex gap-1 pt-1 border-t border-neutral-200 dark:border-neutral-800">
          {([['read', 'Lido'], ['reading', 'Lendo'], ['wishlist', 'Desejos']] as const).map(([s, label]) => (
            <button
              key={s}
              onClick={() => onStatusChange(userBook.id, s)}
              disabled={userBook.status === s}
              className={`flex-1 text-xs py-1 rounded transition-colors ${
                userBook.status === s
                  ? 'bg-neutral-200 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500 cursor-default'
                  : 'text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
