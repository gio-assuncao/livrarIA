import { Link } from 'react-router-dom'
import { FiPlus } from 'react-icons/fi'
import { useState } from 'react'
import { useBooks, useUpdateBook, useDeleteBook } from '../hooks/useBooks'
import BookGrid from '../components/BookGrid'
import EditBookModal from '../components/EditBookModal'
import type { UserBook, UserBookUpdate } from '../types'

export default function Wishlist() {
  const { data, isLoading } = useBooks('wishlist')
  const updateBook = useUpdateBook()
  const deleteBook = useDeleteBook()
  const [editingBook, setEditingBook] = useState<UserBook | null>(null)

  const handleStatus = (id: number, status: string) =>
    updateBook.mutate({ id, data: { status } })

  const handleRate = (id: number, rating: number) =>
    updateBook.mutate({ id, data: { rating } })

  const handleDelete = (id: number) => deleteBook.mutate(id)

  const handleSaveEdit = (id: number, data: UserBookUpdate) => {
    updateBook.mutate({ id, data }, { onSuccess: () => setEditingBook(null) })
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {editingBook && (
        <EditBookModal
          userBook={editingBook}
          onSave={handleSaveEdit}
          onClose={() => setEditingBook(null)}
          isSaving={updateBook.isPending}
        />
      )}

      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Lista de Desejos</h1>
          <p className="text-neutral-500 text-sm mt-1">Livros que você quer ler.</p>
        </div>
        <Link
          to="/add"
          className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
        >
          <FiPlus size={15} />
          Adicionar
        </Link>
      </div>

      {isLoading ? (
        <div className="text-neutral-400 text-sm">Carregando...</div>
      ) : (
        <BookGrid
          books={data ?? []}
          onRate={handleRate}
          onStatusChange={handleStatus}
          onDelete={handleDelete}
          onEdit={setEditingBook}
          emptyMessage="Sua lista de desejos está vazia. Pesquise livros e adicione!"
        />
      )}
    </div>
  )
}
