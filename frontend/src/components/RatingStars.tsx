import { FiStar } from 'react-icons/fi'
import { FaStar } from 'react-icons/fa'

interface Props {
  rating: number | null
  onRate?: (n: number) => void
  size?: number
}

export default function RatingStars({ rating, onRate, size = 15 }: Props) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(n => {
        const filled = rating !== null && n <= rating
        return (
          <button
            key={n}
            type="button"
            onClick={() => onRate?.(n)}
            disabled={!onRate}
            className={`transition-colors ${
              onRate ? 'cursor-pointer hover:scale-110' : 'cursor-default'
            } ${filled ? 'text-amber-400' : 'text-neutral-600'}`}
          >
            {filled ? <FaStar size={size} /> : <FiStar size={size} />}
          </button>
        )
      })}
    </div>
  )
}
