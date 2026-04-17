import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchUserBooks, createBook, updateUserBook, deleteBook } from '../api/client'
import type { AddBookPayload, UserBookUpdate } from '../types'

export function useBooks(status?: string) {
  return useQuery({
    queryKey: ['books', status ?? 'all'],
    queryFn: () => fetchUserBooks(status),
    staleTime: 1000 * 30,
  })
}

export function useCreateBook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AddBookPayload) => createBook(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['books'] }),
  })
}

export function useUpdateBook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserBookUpdate }) =>
      updateUserBook(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['books'] })
      qc.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })
}

export function useDeleteBook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteBook(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['books'] })
      qc.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })
}
