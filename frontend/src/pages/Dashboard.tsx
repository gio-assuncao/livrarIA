import { useState } from 'react'
import { FiPlus, FiCheck, FiCompass, FiRefreshCw } from 'react-icons/fi'
import { useBooks, useUpdateBook, useDeleteBook } from '../hooks/useBooks'
import { useRecommendations, useDiscover, useImportRecommendation } from '../hooks/useRecommendations'
import BookGrid from '../components/BookGrid'
import EditBookModal from '../components/EditBookModal'
import type { RecommendationItem, UserBook, UserBookUpdate } from '../types'

interface RecCardProps {
  rec: RecommendationItem
  onImport: (rec: RecommendationItem) => void
  importing: boolean
  imported: boolean
}

function RecommendationCard({ rec, onImport, importing, imported }: RecCardProps) {
  return (
    <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 hover:border-violet-300 dark:hover:border-violet-800 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        {rec.cover_url && (
          <img
            src={rec.cover_url}
            alt=""
            className="w-12 h-[4.5rem] object-cover rounded shadow-sm shrink-0 bg-neutral-200 dark:bg-neutral-800"
            loading="lazy"
            onError={e => { e.currentTarget.style.display = 'none' }}
          />
        )}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-neutral-900 dark:text-neutral-100 text-sm truncate" title={rec.title}>{rec.title}</h3>
          <p className="text-neutral-500 dark:text-neutral-400 text-xs mt-0.5 truncate">{rec.author}</p>
        </div>
        <span
          className="text-xs bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 border border-violet-300 dark:border-violet-800 px-2 py-0.5 rounded font-mono shrink-0"
          title={`Semântica ${(rec.semantic_score * 100).toFixed(0)}% · Gêneros ${(rec.category_score * 100).toFixed(0)}%`}
        >
          {(rec.semantic_score * 100).toFixed(0)}%
        </span>
      </div>
      {rec.description && (
        <p className="text-neutral-500 text-xs line-clamp-2 mb-2 leading-relaxed">
          {rec.description}
        </p>
      )}
      <p className="text-violet-600/70 dark:text-violet-400/70 text-xs italic leading-relaxed">{rec.reason}</p>
      {rec.categories.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {rec.categories.slice(0, 2).map(c => (
            <span key={c} className="text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-500 px-2 py-0.5 rounded-full">
              {c}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-neutral-400 dark:text-neutral-600 capitalize">{rec.source.replace('_', ' ')}</span>
        <button
          onClick={() => onImport(rec)}
          disabled={importing || imported}
          className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg transition-colors ${
            imported
              ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400 cursor-default'
              : 'bg-violet-600 hover:bg-violet-500 disabled:opacity-60 text-white'
          }`}
        >
          {imported ? <FiCheck size={12} /> : <FiPlus size={12} />}
          {importing ? 'Adicionando...' : imported ? 'Na lista' : 'Quero ler'}
        </button>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const reading = useBooks('reading')
  const read = useBooks('read')
  const recs = useRecommendations(5)
  const discover = useDiscover()
  const importRec = useImportRecommendation()
  const updateBook = useUpdateBook()
  const deleteBook = useDeleteBook()

  const [editingBook, setEditingBook] = useState<UserBook | null>(null)
  const [importedKeys, setImportedKeys] = useState<Set<string>>(new Set())
  const [importingKey, setImportingKey] = useState<string | null>(null)

  const recKey = (rec: RecommendationItem) => `${rec.source}:${rec.external_id}`

  const handleImportRec = async (rec: RecommendationItem) => {
    const key = recKey(rec)
    setImportingKey(key)
    try {
      await importRec.mutateAsync({ rec })
      setImportedKeys(prev => new Set([...prev, key]))
    } catch {
      // error surfaced via importRec.isError below
    } finally {
      setImportingKey(null)
    }
  }

  const hasHistory = (reading.data?.length ?? 0) + (read.data?.length ?? 0) > 0

  const handleRate = (id: number, rating: number) =>
    updateBook.mutate({ id, data: { rating } })

  const handleStatus = (id: number, status: string) =>
    updateBook.mutate({ id, data: { status } })

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

      <div className="flex gap-8">
        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-10">
          <section>
            <h2 className="text-base font-semibold text-neutral-700 dark:text-neutral-300 mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
              Lendo Agora
              {!reading.isLoading && (
                <span className="text-neutral-400 dark:text-neutral-600 font-normal text-sm ml-1">
                  ({reading.data?.length ?? 0})
                </span>
              )}
            </h2>
            {reading.isLoading ? (
              <div className="text-neutral-400 text-sm">Carregando...</div>
            ) : (
              <BookGrid
                books={reading.data ?? []}
                onRate={handleRate}
                onStatusChange={handleStatus}
                onDelete={handleDelete}
                onEdit={setEditingBook}
                emptyMessage="Você não está lendo nada no momento."
              />
            )}
          </section>

          <section>
            <h2 className="text-base font-semibold text-neutral-700 dark:text-neutral-300 mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
              Lidos
              {!read.isLoading && (
                <span className="text-neutral-400 dark:text-neutral-600 font-normal text-sm ml-1">
                  ({read.data?.length ?? 0})
                </span>
              )}
            </h2>
            {read.isLoading ? (
              <div className="text-neutral-400 text-sm">Carregando...</div>
            ) : (
              <BookGrid
                books={read.data ?? []}
                onRate={handleRate}
                onStatusChange={handleStatus}
                onDelete={handleDelete}
                onEdit={setEditingBook}
                emptyMessage="Nenhum livro marcado como lido ainda. Adicione alguns!"
              />
            )}
          </section>
        </div>

        {/* Recommendations sidebar */}
        <aside className="w-72 shrink-0 hidden lg:block">
          <div className="sticky top-20">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-neutral-700 dark:text-neutral-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-violet-400 inline-block" />
                Para Você
              </h2>
              {hasHistory && (
                <button
                  onClick={() => discover.mutate()}
                  disabled={discover.isPending}
                  title="Busca novos livros nas fontes externas com base nos seus autores e gêneros favoritos"
                  className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 hover:text-violet-600 dark:hover:text-violet-300 transition-colors px-2 py-1 rounded disabled:opacity-60"
                >
                  {discover.isPending ? <FiRefreshCw size={13} className="animate-spin" /> : <FiCompass size={13} />}
                  {discover.isPending ? 'Buscando...' : 'Descobrir mais'}
                </button>
              )}
            </div>

            {discover.data && (
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mb-3">
                {discover.data.new_books > 0
                  ? `${discover.data.new_books} livros novos no catálogo (${discover.data.catalog_size} no total).`
                  : `Nada novo desta vez — catálogo com ${discover.data.catalog_size} livros.`}
              </p>
            )}
            {(discover.isError || importRec.isError) && (
              <p className="text-xs text-red-400 mb-3">Não foi possível falar com o servidor. Tente de novo.</p>
            )}

            {recs.isLoading ? (
              <div className="text-neutral-400 text-sm">Calculando recomendações...</div>
            ) : recs.data && recs.data.length > 0 ? (
              <div className="space-y-3">
                {recs.data.map(rec => (
                  <RecommendationCard
                    key={rec.id}
                    rec={rec}
                    onImport={handleImportRec}
                    importing={importingKey === recKey(rec)}
                    imported={importedKeys.has(recKey(rec))}
                  />
                ))}
              </div>
            ) : hasHistory ? (
              <div className="text-neutral-400 dark:text-neutral-600 text-sm space-y-2">
                <p>O catálogo ainda está vazio.</p>
                <p>Clique em <span className="text-neutral-600 dark:text-neutral-400">Descobrir mais</span> ou pesquise livros na aba Adicionar — cada busca alimenta as recomendações.</p>
              </div>
            ) : (
              <p className="text-neutral-400 dark:text-neutral-600 text-sm">
                Adicione e avalie livros que você leu para receber recomendações personalizadas.
              </p>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
