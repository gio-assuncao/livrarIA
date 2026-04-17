import { useQuery } from '@tanstack/react-query'
import { getRecommendations } from '../api/client'

export function useRecommendations(limit = 10, genre?: string) {
  return useQuery({
    queryKey: ['recommendations', limit, genre],
    queryFn: () => getRecommendations(limit, genre),
    staleTime: 1000 * 60 * 2,
    retry: false,
  })
}
