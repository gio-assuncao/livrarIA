import { useRef, useState } from 'react'
import { FiX, FiStar } from 'react-icons/fi'
import { useBooks, useUpdateBook } from '../hooks/useBooks'
import type { UserBook } from '../types'

const CONFETTI_COLORS = ['#a78bfa', '#f0abfc', '#fbbf24', '#67e8f9', '#ffffff', '#f472b6']
const SPARKLE_COLORS = ['#fde68a', '#fef3c7', '#a78bfa', '#ffffff']

/** Deterministic per-book visual traits, so stickers look stable across renders. */
function stickerTraits(id: number) {
  return {
    rotation: ((id * 37) % 13) - 6, // -6deg .. +6deg
    hue: (id * 137.508) % 360, // golden-angle spread for coverless stickers
  }
}

function initials(title: string): string {
  return title
    .split(/\s+/)
    .filter(w => w.length > 2 || /^[A-ZÀ-Ú]/.test(w))
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase() ?? '')
    .join('')
}

function reducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Spawn a one-shot particle burst inside `host` (must be positioned). */
function burst(host: HTMLElement, colors: string[], count: number, spread: number) {
  for (let i = 0; i < count; i++) {
    const p = document.createElement('span')
    const angle = (i / count) * Math.PI * 2 + Math.random() * 0.7
    const dist = spread * (0.5 + Math.random() * 0.9)
    p.className = 'particle'
    p.style.background = colors[i % colors.length]
    p.style.setProperty('--dx', `${Math.cos(angle) * dist}px`)
    p.style.setProperty('--dy', `${Math.sin(angle) * dist - spread * 0.35}px`)
    p.style.setProperty('--rot', `${(Math.random() * 2 - 1) * 300}deg`)
    p.style.animationDelay = `${Math.random() * 100}ms`
    host.appendChild(p)
    setTimeout(() => p.remove(), 1000)
  }
}

function Sticker({ userBook, justPasted }: { userBook: UserBook; justPasted: boolean }) {
  const { book, rating } = userBook
  const { rotation, hue } = stickerTraits(userBook.id)
  const isHolo = rating === 5

  return (
    <div style={{ transform: `rotate(${rotation}deg)` }} className="w-full h-full">
      <div
        className={`relative w-full h-full p-1 bg-white rounded-lg shadow-md overflow-hidden ${justPasted ? 'sticker-paste' : ''}`}
        title={`${book.title} — ${book.author}${isHolo ? ' ★ figurinha brilhante!' : ''}`}
      >
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt={book.title}
            className="w-full h-full object-cover rounded"
            loading="lazy"
            onError={e => { e.currentTarget.style.display = 'none' }}
          />
        ) : (
          <div
            className="w-full h-full rounded flex flex-col items-center justify-center gap-1 p-1 text-center"
            style={{ background: `linear-gradient(160deg, hsl(${hue} 70% 55%), hsl(${(hue + 40) % 360} 70% 40%))` }}
          >
            <span className="text-white font-bold text-lg drop-shadow">{initials(book.title)}</span>
            <span className="text-white/90 text-[9px] leading-tight line-clamp-2">{book.title}</span>
          </div>
        )}
        {isHolo && <div className="holo-overlay absolute inset-0 rounded pointer-events-none" />}
      </div>
    </div>
  )
}

export default function Album() {
  const { data, isLoading } = useBooks('read')
  const updateBook = useUpdateBook()
  const [justPastedId, setJustPastedId] = useState<number | null>(null)
  // Stickers currently flying from the pack to their slot: the slot keeps
  // rendering as empty and the tray button stays hidden until landing.
  const [inFlight, setInFlight] = useState<Set<number>>(new Set())
  // Never-revealed stickers live inside a sealed pack; opening it is permanent
  // (server-side revealed_at). justRevealed bridges the animation → refetch gap.
  const [justRevealed, setJustRevealed] = useState<Set<number>>(new Set())
  const [packAnimating, setPackAnimating] = useState(false)
  const packRef = useRef<HTMLButtonElement>(null)

  // Collection order: the older the read, the earlier the slot
  const collection = [...(data ?? [])].sort((a, b) => a.id - b.id)
  const pasted = collection.filter(ub => ub.pasted_at)
  const unpasted = collection.filter(ub => !ub.pasted_at)
  const isRevealed = (ub: UserBook) => Boolean(ub.revealed_at) || justRevealed.has(ub.id)
  const tray = unpasted.filter(isRevealed)
  const packContents = unpasted.filter(ub => !isRevealed(ub))

  // ── Pack opening ───────────────────────────────────────────────────────────

  const openPack = async () => {
    const el = packRef.current
    const ids = packContents.map(ub => ub.id)
    if (!el || packAnimating || ids.length === 0) return

    const commitReveal = () => {
      setJustRevealed(prev => {
        const next = new Set(prev)
        for (const id of ids) next.add(id)
        return next
      })
      for (const id of ids) updateBook.mutate({ id, data: { revealed: true } })
    }

    if (reducedMotion() || typeof el.animate !== 'function') {
      commitReveal()
      return
    }
    setPackAnimating(true)

    // 1. Excited shake
    await el.animate(
      [
        { transform: 'rotate(0deg)' },
        { transform: 'translateX(-3px) rotate(-3deg)' },
        { transform: 'translateX(3px) rotate(3deg)' },
        { transform: 'translateX(-4px) rotate(-3deg)' },
        { transform: 'translateX(4px) rotate(3deg)' },
        { transform: 'rotate(0deg)' },
      ],
      { duration: 340, easing: 'ease-in-out' },
    ).finished

    // 2. Tear strip flies off + confetti erupts
    const strip = el.querySelector<HTMLElement>('[data-strip]')
    strip?.animate(
      [
        { transform: 'translate(0, 0) rotate(0deg)', opacity: 1 },
        { transform: 'translate(46px, -90px) rotate(35deg)', opacity: 0 },
      ],
      { duration: 380, easing: 'cubic-bezier(0.2, 0.6, 0.4, 1)', fill: 'forwards' },
    )
    burst(el, CONFETTI_COLORS, 22, 110)

    // 3. Pack body evaporates
    await el.animate(
      [
        { transform: 'scale(1)', opacity: 1 },
        { transform: 'scale(1.15)', opacity: 0 },
      ],
      { duration: 340, delay: 140, easing: 'ease-out', fill: 'forwards' },
    ).finished

    commitReveal()
    setPackAnimating(false)
  }

  // ── Paste flight ───────────────────────────────────────────────────────────

  const land = (id: number, slotEl: HTMLElement | null) => {
    setInFlight(prev => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
    setJustPastedId(id)
    if (slotEl && !reducedMotion()) burst(slotEl, SPARKLE_COLORS, 10, 44)
  }

  const paste = (ub: UserBook, e: React.MouseEvent<HTMLButtonElement>) => {
    const srcEl = e.currentTarget
    const destEl = document.querySelector<HTMLElement>(`[data-slot-id="${ub.id}"]`)

    updateBook.mutate({ id: ub.id, data: { pasted: true } })

    if (!destEl || reducedMotion() || typeof srcEl.animate !== 'function') {
      setJustPastedId(ub.id)
      return
    }

    const src = srcEl.getBoundingClientRect()
    const dst = destEl.getBoundingClientRect()
    const scale = dst.width / src.width
    const dx = dst.left - src.left + (dst.width - src.width) / 2
    const dy = dst.top - src.top + (dst.height - src.height) / 2

    // Three layers so X and Y run on independent easings → true parabolic arc:
    //   wrapper: horizontal glide   mid: vertical arc + wobble   clone: shadow depth
    const wrapper = document.createElement('div')
    const mid = document.createElement('div')
    const clone = srcEl.firstElementChild!.cloneNode(true) as HTMLElement
    Object.assign(wrapper.style, {
      position: 'fixed',
      left: `${src.left}px`,
      top: `${src.top}px`,
      width: `${src.width}px`,
      height: `${src.height}px`,
      zIndex: '100',
      pointerEvents: 'none',
      willChange: 'transform',
    })
    Object.assign(mid.style, { width: '100%', height: '100%', willChange: 'transform' })
    mid.appendChild(clone)
    wrapper.appendChild(mid)
    document.body.appendChild(wrapper)
    srcEl.style.visibility = 'hidden'
    setInFlight(prev => new Set(prev).add(ub.id))

    const D = 850
    const peak = dy - 90 // apex: 90px above the destination slot

    // Horizontal: smooth glide
    wrapper.animate(
      [{ transform: 'translateX(0)' }, { transform: `translateX(${dx}px)` }],
      { duration: D, easing: 'cubic-bezier(0.45, 0.05, 0.55, 0.95)', fill: 'forwards' },
    )

    // Vertical: peel off the page, soar past the apex, drop onto the slot
    const arc = mid.animate(
      [
        { transform: 'translateY(0) scale(1) rotate(0deg)' },
        // peel: quick squash as the sticker is plucked off
        { transform: 'translateY(3px) scale(0.93) rotate(-2deg)', offset: 0.07, easing: 'cubic-bezier(0.3, 0, 0.6, 1)' },
        // rising, tilting into the wind
        { transform: `translateY(${peak * 0.55}px) scale(${1 + (scale - 1) * 0.45}) rotate(-8deg)`, offset: 0.34, easing: 'cubic-bezier(0.2, 0.6, 0.35, 1)' },
        // apex: floating for an instant, counter-tilt
        { transform: `translateY(${peak}px) scale(${1 + (scale - 1) * 0.8}) rotate(7deg)`, offset: 0.62, easing: 'cubic-bezier(0.35, 0, 0.85, 0.45)' },
        // gravity drop onto the page
        { transform: `translateY(${dy}px) scale(${scale}) rotate(0deg)` },
      ],
      { duration: D, easing: 'linear', fill: 'forwards' },
    )

    // Shadow tracks altitude: tight → far and soft → snapped tight on impact
    clone.animate(
      [
        { filter: 'drop-shadow(0 2px 2px rgba(0,0,0,0.35))' },
        { filter: 'drop-shadow(0 34px 26px rgba(0,0,0,0.22))', offset: 0.62 },
        { filter: 'drop-shadow(0 1px 1px rgba(0,0,0,0.45))' },
      ],
      { duration: D, fill: 'forwards' },
    )

    const finish = () => {
      wrapper.remove()
      land(ub.id, destEl)
    }
    arc.onfinish = finish
    // Safety net: never leave a sticker stranded mid-air (tab switch, etc.)
    arc.oncancel = finish
  }

  const peel = (ub: UserBook) => {
    if (justPastedId === ub.id) setJustPastedId(null)
    updateBook.mutate({ id: ub.id, data: { pasted: false } })
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-2 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">Álbum de Figurinhas</h1>
          <p className="text-neutral-500 text-sm mt-1">
            Cada livro lido vira uma figurinha. Livros 5★ viram figurinhas brilhantes.
          </p>
        </div>
        {collection.length > 0 && (
          <span className="text-sm text-neutral-500 shrink-0 font-mono">
            {pasted.length}/{collection.length} coladas
          </span>
        )}
      </div>

      {/* Progress */}
      {collection.length > 0 && (
        <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-800 mb-8 overflow-hidden">
          <div
            className="h-full rounded-full bg-violet-500 transition-all duration-500"
            style={{ width: `${(pasted.length / collection.length) * 100}%` }}
          />
        </div>
      )}

      {isLoading ? (
        <div className="text-neutral-400 text-sm">Carregando...</div>
      ) : collection.length === 0 ? (
        <div className="text-neutral-500 text-sm py-16 text-center">
          Nenhuma figurinha ainda — marque livros como <span className="font-medium">Lido</span> para ganhá-las!
        </div>
      ) : (
        <>
          {/* Album pages: one numbered slot per read book */}
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4 p-5 rounded-2xl bg-amber-50 dark:bg-neutral-900 border-2 border-amber-200/70 dark:border-neutral-800">
            {collection.map((ub, i) => (
              <div key={ub.id} data-slot-id={ub.id} className="relative aspect-[3/4] group">
                {(ub.pasted_at || justPastedId === ub.id) && !inFlight.has(ub.id) ? (
                  <>
                    <Sticker userBook={ub} justPasted={justPastedId === ub.id} />
                    <button
                      onClick={() => peel(ub)}
                      aria-label={`Descolar ${ub.book.title}`}
                      className="absolute -top-1.5 -right-1.5 z-10 hidden group-hover:flex items-center justify-center w-5 h-5 rounded-full bg-neutral-700 text-white shadow hover:bg-red-500 transition-colors"
                    >
                      <FiX size={11} />
                    </button>
                  </>
                ) : (
                  <div
                    className={`w-full h-full rounded-lg border-2 border-dashed border-amber-300 dark:border-neutral-700 flex flex-col items-center justify-center gap-1 ${inFlight.has(ub.id) ? 'slot-target' : ''}`}
                  >
                    <span className="text-2xl text-amber-300 dark:text-neutral-700 select-none">?</span>
                    <span className="text-[10px] font-mono text-amber-400/80 dark:text-neutral-600">nº {i + 1}</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Sealed pack: stickers never revealed before */}
          {packContents.length > 0 && (
            <div className="mt-10 flex flex-col items-center gap-3">
              <button
                ref={packRef}
                onClick={openPack}
                disabled={packAnimating}
                aria-label={`Abrir pacote com ${packContents.length} figurinha${packContents.length > 1 ? 's' : ''}`}
                className="relative w-44 aspect-[3/4] cursor-pointer hover:scale-105 hover:-rotate-1 transition-transform"
              >
                {/* Tear strip */}
                <div
                  data-strip
                  className="absolute top-0 inset-x-0 h-8 rounded-t-xl bg-gradient-to-r from-violet-700 to-fuchsia-600 border-b-2 border-dashed border-white/70 flex items-center justify-center text-[10px] font-semibold text-white/90 tracking-[0.2em] select-none z-10"
                >
                  ✂ PUXE AQUI
                </div>
                {/* Pack body */}
                <div className="absolute inset-x-0 top-8 bottom-0 rounded-b-xl bg-gradient-to-br from-violet-600 via-fuchsia-500 to-amber-400 shadow-xl overflow-hidden flex flex-col items-center justify-center gap-2">
                  <div className="foil-shine absolute inset-0 pointer-events-none" />
                  <FiStar size={34} className="text-white drop-shadow" />
                  <span className="text-white font-bold text-sm tracking-widest drop-shadow">FIGURINHAS</span>
                  <span className="text-white/80 text-[10px] tracking-wider">LivrarIA</span>
                </div>
                {/* Count badge */}
                <span className="absolute -top-2 -right-2 z-20 min-w-6 h-6 px-1.5 rounded-full bg-amber-400 text-amber-950 text-xs font-bold flex items-center justify-center shadow">
                  {packContents.length}
                </span>
              </button>
              <p className="text-sm text-neutral-500">
                Você ganhou {packContents.length === 1 ? 'uma figurinha nova' : `${packContents.length} figurinhas novas`} — clique no pacote para abrir!
              </p>
            </div>
          )}

          {/* Tray: revealed stickers waiting to be pasted */}
          {tray.length > 0 && (
            <div className="mt-8">
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
                Figurinhas para colar <span className="text-neutral-400">— clique para colar no álbum</span>
              </h2>
              <div className="flex flex-wrap gap-3">
                {tray.map((ub, i) => (
                  <button
                    key={ub.id}
                    onClick={e => paste(ub, e)}
                    disabled={updateBook.isPending}
                    aria-label={`Colar ${ub.book.title}`}
                    style={{ animationDelay: `${i * 90}ms` }}
                    className="sticker-reveal w-20 aspect-[3/4] cursor-pointer hover:scale-105 hover:-translate-y-1 transition-transform disabled:opacity-60"
                  >
                    <Sticker userBook={ub} justPasted={false} />
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
