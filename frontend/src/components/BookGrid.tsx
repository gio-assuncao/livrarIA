import type { UserBook } from '../types'
import BookCard from './BookCard'

interface Props {
  books: UserBook[]
  onRate?: (id: number, rating: number) => void
  onStatusChange?: (id: number, status: string) => void
  onDelete?: (id: number) => void
  onEdit?: (userBook: UserBook) => void
  emptyMessage?: string
}

export default function BookGrid({ books, onRate, onStatusChange, onDelete, onEdit, emptyMessage }: Props) {
  if (books.length === 0) {
    return (
      <div className="col-span-full text-center py-12 text-neutral-400 dark:text-neutral-600">
        {emptyMessage ?? 'Nenhum livro aqui ainda.'}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {books.map(ub => (
        <BookCard
          key={ub.id}
          userBook={ub}
          onRate={onRate}
          onStatusChange={onStatusChange}
          onDelete={onDelete}
          onEdit={onEdit}
        />
      ))}
    </div>
  )
}
