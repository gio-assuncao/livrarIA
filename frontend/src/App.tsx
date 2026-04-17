import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import NavBar from './components/NavBar'
import Dashboard from './pages/Dashboard'
import Wishlist from './pages/Wishlist'
import AddBook from './pages/AddBook'
import Chat from './pages/Chat'
import { useTheme } from './hooks/useTheme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function AppInner() {
  const { isDark, toggle } = useTheme()

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100">
        <NavBar isDark={isDark} onToggleTheme={toggle} />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/wishlist" element={<Wishlist />} />
          <Route path="/add" element={<AddBook />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
