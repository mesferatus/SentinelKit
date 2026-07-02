import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps only the user profile in memory and clears it on logout', async () => {
    const auth = useAuthStore()
    const post = vi.fn()
      .mockResolvedValueOnce({ data: { user: { name: 'Sofia' } } })
      .mockResolvedValueOnce({ status: 204 })

    await auth.login({ email: 'sofia@example.com', password: 'Segura123' }, { post })
    expect(auth.user.name).toBe('Sofia')
    expect(auth.isAuthenticated).toBe(true)
    expect('accessToken' in auth).toBe(false)
    expect(localStorage.getItem('access_token')).toBeNull()

    await auth.logout({ post })
    expect(auth.user).toBeNull()
    expect(auth.isAuthenticated).toBe(false)
  })

  it('returns a clear API error message', async () => {
    const auth = useAuthStore()
    const client = {
      post: vi.fn().mockRejectedValue({ response: { data: { detail: 'Credenciais inválidas' } } }),
    }

    await expect(auth.login({ email: 'x@y.com', password: 'errada123' }, client))
      .rejects.toThrow('Credenciais inválidas')
  })

  it('updates the profile kept in memory', async () => {
    const auth = useAuthStore()
    auth.user = { id: 1, name: 'Sofia', email: 'sofia@example.com' }
    const client = {
      patch: vi.fn().mockResolvedValue({
        data: { id: 1, name: 'Sofia Lima', email: 'sofia.lima@example.com' },
      }),
    }

    await auth.updateProfile({ name: 'Sofia Lima', email: 'sofia.lima@example.com' }, client)

    expect(client.patch).toHaveBeenCalledWith('/auth/profile', {
      name: 'Sofia Lima',
      email: 'sofia.lima@example.com',
    })
    expect(auth.user.name).toBe('Sofia Lima')
    expect(auth.user.email).toBe('sofia.lima@example.com')
  })
})
