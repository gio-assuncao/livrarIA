import { NavLink } from 'react-router-dom'
import { FiBook, FiHeart, FiPlusCircle, FiMessageSquare, FiSun, FiMoon } from 'react-icons/fi'

const links = [
  { to: '/', label: 'Início', icon: FiBook },
  { to: '/wishlist', label: 'Lista de Desejos', icon: FiHeart },
  { to: '/add', label: 'Adicionar', icon: FiPlusCircle },
  { to: '/chat', label: 'Chat', icon: FiMessageSquare },
]

interface Props {
  isDark: boolean
  onToggleTheme: () => void
}

export default function NavBar({ isDark, onToggleTheme }: Props) {
  return (
    <nav className="sticky top-0 z-50 bg-white/80 dark:bg-neutral-900/80 backdrop-blur border-b border-neutral-200 dark:border-neutral-800">
      <div className="max-w-6xl mx-auto px-4 flex items-center h-14 gap-8">
        <span className="text-violet-600 dark:text-violet-400 font-bold text-lg tracking-tight select-none">
          LivrarIA
        </span>
        <div className="flex gap-1 flex-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  isActive
                    ? 'bg-violet-100 dark:bg-violet-600/20 text-violet-700 dark:text-violet-300'
                    : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                }`
              }
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </div>
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-lg text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          aria-label="Alternar tema"
        >
          {isDark ? <FiSun size={16} /> : <FiMoon size={16} />}
        </button>
      </div>
    </nav>
  )
}
