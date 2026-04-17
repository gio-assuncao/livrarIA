const config: Record<string, { label: string; className: string }> = {
  read: { label: 'Lido', className: 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800' },
  reading: { label: 'Lendo', className: 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-800' },
  wishlist: { label: 'Lista de Desejos', className: 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800' },
}

interface Props {
  status: string
}

export default function StatusBadge({ status }: Props) {
  const { label, className } = config[status] ?? {
    label: status,
    className: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border-neutral-300 dark:border-neutral-700',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${className}`}>
      {label}
    </span>
  )
}
