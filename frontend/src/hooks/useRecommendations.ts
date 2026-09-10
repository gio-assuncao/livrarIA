import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRecommendations, discoverBooks, importBook } from '../api/client'
import type { RecommendationItem } from '../types'

export function useRecommendations(limit = 10, genre?: string) {
  return useQuery({
    queryKey: ['recommendations', limit, genre],
    queryFn: () => getRecommendations(limit, genre),
    staleTime: 1000 * 60 * 2,
    retry: false,
  })
}

/** Searches external APIs for the user's top authors/categories, then refreshes recommendations. */
export function useDiscover() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: discoverBooks,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recommendations'] }),
  })
}

/** Imports a recommended catalog book into the library (wishlist by default). */
export function useImportRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ rec, status = 'wishlist' }: { rec: RecommendationItem; status?: string }) =>
      importBook(rec.external_id, rec.source, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['books'] })
      qc.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })
}
