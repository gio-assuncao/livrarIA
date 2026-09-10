import { useState } from 'react'
import { FiSearch, FiPlus, FiCheck } from 'react-icons/fi'
import { useCreateBook } from '../hooks/useBooks'
import { searchExternal, importBook } from '../api/client'
import type { ExternalSearchResult, AddBookPayload } from '../types'


export default function AddBook() {
  // Manual form
  const [form, setForm] = useState<AddBookPayload>({
    title: '',
    author: '',
    description: '',
    categories: [],
    status: 'read',
    rating: undefined,
    tags: [],
  })
  const [categoriesInput, setCategoriesInput] = useState('')
  const [tagsInput, setTagsInput] = useState('')
  const createBook = useCreateBook()
  const [addedManual, setAddedManual] = useState(false)

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const payload: AddBookPayload = {
      ...form,
      categories: categoriesInput.split(',').map(s => s.trim()).filter(Boolean),
      tags: tagsInput.split(',').map(s => s.trim()).filter(Boolean),
    }
    await createBook.mutateAsync(payload)
    setForm({ title: '', author: '', description: '', categories: [], status: 'read', tags: [] })
    setCategoriesInput('')
    setTagsInput('')
    setAddedManual(true)
    setTimeout(() => setAddedManual(false), 2500)
  }

  // External search
  const [query, setQuery] = useState('')
  const [searchSource, setSearchSource] = useState('all')
  const [searchResults, setSearchResults] = useState<ExternalSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [importedIds, setImportedIds] = useState<Set<string>>(new Set())
  const [importingId, setImportingId] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setIsSearching(true)
    try {
      const results = await searchExternal(query.trim(), searchSource)
      setSearchResults(results)
    } finally {
      setIsSearching(false)
    }
  }

  const handleImport = async (result: ExternalSearchResult) => {
    setImportingId(result.external_id)
    try {
      await importBook(result.external_id, result.source, 'wishlist')
      setImportedIds(prev => new Set([...prev, result.external_id]))
    } finally {
      setImportingId(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-10">
      {/* Manual Add */}
      <section>
        <h1 className="text-xl font-bold text-neutral-100 mb-1">Adicionar Livro Manualmente</h1>
        <p className="text-neutral-500 text-sm mb-6">Preencha os detalhes do livro diretamente.</p>

        <form onSubmit={handleManualSubmit} className="max-w-xl space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-neutral-400 mb-1 block">Título *</label>
              <input
                required
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                className="w-full bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-600 focus:outline-none focus:border-violet-500"
                placeholder="Título do livro"
              />
            </div>
            <div>
              <label className="text-xs text-neutral-400 mb-1 block">Autor *</label>
              <input
                required
                value={form.author}
                onChange={e => setForm(f => ({ ...f, author: e.target.value }))}
                className="w-full bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-600 focus:outline-none focus:border-violet-500"
                placeholder="Nome do autor"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-neutral-400 mb-1 block">Descrição</label>
            <textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={3}
              className="w-full bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-600 focus:outline-none focus:border-violet-500 resize-none"
              placeholder="Breve descrição..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-neutral-400 mb-1 block">Categorias (separadas por vírgula)</label>
              <input
                value={categoriesInput}
                onChange={e => setCategoriesInput(e.target.value)}
                className="w-full bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-600 focus:outline-none focus:border-violet-500"
                placeholder="Ficção, Thriller"
              />
            </div>
            <div>
              <label className="text-xs text-neutral-400 mb-1 block">Tags (separadas por vírgula)</label>
              <input
                value={tagsInput}
                onChange={e => setTagsInput(e.target.value)}
                className="w-full bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-600 focus:outline-none focus:border-violet-500"
                placeholder="sombrio, rápido"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-neutral-400 mb-1 block">Status</label>
              <select
                value={form.status}
                onChange={e => setForm(f => ({ ...f, status: e.target.value as typeof form.status }))}
                className="w-full bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 focus:outline-none focus:border-violet-600"
              >
                <option value="read">Lido</option>
                <option value="reading">Lendo</option>
                <option value="wishlist">Lista de Desejos</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-neutral-400 mb-1 block">Avaliação (opcional)</label>
              <input
                type="number"
                min={1}
                max={5}
                value={form.rating ?? ''}
                onChange={e => setForm(f => ({ ...f, rating: e.target.value ? Number(e.target.value) : undefined }))}
                className="w-full bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 focus:outline-none focus:border-violet-600"
                placeholder="1–5"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={createBook.isPending}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 disabled:bg-neutral-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {addedManual ? <FiCheck size={15} /> : <FiPlus size={15} />}
            {createBook.isPending ? 'Adicionando...' : addedManual ? 'Adicionado!' : 'Adicionar Livro'}
          </button>
        </form>
      </section>

      {/* External Search */}
      <section>
        <h2 className="text-lg font-semibold text-neutral-100 mb-1">Pesquisar em Bibliotecas Externas</h2>
        <p className="text-neutral-500 text-sm mb-6">Encontre livros no Google Books e Open Library.</p>

        <form onSubmit={handleSearch} className="flex gap-3 max-w-xl mb-6">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="flex-1 bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-violet-600"
            placeholder="Pesquise por título, autor ou tema..."
          />
          <select
            value={searchSource}
            onChange={e => setSearchSource(e.target.value)}
            className="bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 focus:outline-none focus:border-violet-600"
          >
            <option value="all">Todas as Fontes</option>
            <option value="google_books">Google Books</option>
            <option value="open_library">Open Library</option>
          </select>
          <button
            type="submit"
            disabled={isSearching}
            className="flex items-center gap-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <FiSearch size={15} />
            {isSearching ? 'Buscando...' : 'Buscar'}
          </button>
        </form>

        {searchResults.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {searchResults.map(result => {
              const isImported = importedIds.has(result.external_id)
              const isImporting = importingId === result.external_id
              return (
                <div
                  key={`${result.source}-${result.external_id}`}
                  className="p-4 rounded-xl bg-neutral-900 border border-neutral-800 flex flex-col gap-3"
                >
                  <div className="flex items-start gap-3">
                    {result.cover_url && (
                      <img
                        src={result.cover_url}
                        alt=""
                        className="w-12 h-[4.5rem] object-cover rounded shadow-sm shrink-0 bg-neutral-800"
                        loading="lazy"
                        onError={e => { e.currentTarget.style.display = 'none' }}
                      />
                    )}
                    <div className="min-w-0">
                      <h3 className="font-semibold text-neutral-100 text-sm leading-tight">
                        {result.title}
                      </h3>
                      <p className="text-neutral-400 text-xs mt-0.5">{result.author ?? 'Autor desconhecido'}</p>
                    </div>
                  </div>
                  {result.description && (
                    <p className="text-neutral-500 text-xs line-clamp-3 leading-relaxed">
                      {result.description}
                    </p>
                  )}
                  {result.categories.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {result.categories.slice(0, 3).map(c => (
                        <span key={c} className="text-xs bg-neutral-800 text-neutral-500 px-2 py-0.5 rounded-full">
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center justify-between mt-auto">
                    <span className="text-xs text-neutral-600 capitalize">{result.source.replace('_', ' ')}</span>
                    <button
                      onClick={() => handleImport(result)}
                      disabled={isImported || isImporting}
                      className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors ${
                        isImported
                          ? 'bg-emerald-900/40 text-emerald-400 cursor-default'
                          : 'bg-violet-600 hover:bg-violet-500 text-white'
                      }`}
                    >
                      {isImported ? <FiCheck size={12} /> : <FiPlus size={12} />}
                      {isImporting ? 'Adicionando...' : isImported ? 'Adicionado' : 'Adicionar à Lista'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
