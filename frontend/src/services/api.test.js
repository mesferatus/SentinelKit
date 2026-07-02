import { beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'
import { createPinia, setActivePinia } from 'pinia'

import { api, installAuthInterceptors, setUnauthorizedHandler } from './api'
import { useAuthStore } from '../stores/auth'

describe('API auth interceptors', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    setUnauthorizedHandler(() => {})
  })

  it('uses credentials without exposing an authorization token to JavaScript', async () => {
    const auth = useAuthStore()
    const adapter = vi.fn(async (config) => ({
      config,
      data: {},
      headers: {},
      status: 200,
      statusText: 'OK',
    }))

    installAuthInterceptors(auth)
    await api.get('/dashboard', { adapter })

    expect(api.defaults.withCredentials).toBe(true)
    expect(api.defaults.timeout).toBe(8000)
    expect(adapter.mock.calls[0][0].headers.Authorization).toBeUndefined()
  })

  it('performs one refresh for concurrent 401 responses and retries both requests', async () => {
    const auth = useAuthStore()
    const refresh = vi
      .spyOn(axios, 'post')
      .mockResolvedValue({ data: { user: { name: 'Sofia' } } })
    const attempts = new Map()
    const adapter = vi.fn(async (config) => {
      const count = attempts.get(config.url) ?? 0
      attempts.set(config.url, count + 1)
      if (count === 0) {
        const error = new Error('Unauthorized')
        error.config = config
        error.response = { status: 401 }
        throw error
      }
      return { config, data: config.url, headers: {}, status: 200, statusText: 'OK' }
    })

    installAuthInterceptors(auth)
    const results = await Promise.all([
      api.get('/one', { adapter }),
      api.get('/two', { adapter }),
    ])

    expect(refresh).toHaveBeenCalledTimes(1)
    expect(auth.user.name).toBe('Sofia')
    expect(results.map((result) => result.data)).toEqual(['/one', '/two'])
  })

  it('does not refresh again when the refresh request fails', async () => {
    const auth = useAuthStore()
    vi.spyOn(axios, 'post').mockRejectedValue({
      response: { status: 401 },
      config: { url: '/auth/refresh' },
    })
    const adapter = vi.fn(async (config) => {
      const error = new Error('Unauthorized')
      error.config = config
      error.response = { status: 401 }
      throw error
    })

    installAuthInterceptors(auth)

    await expect(api.get('/private', { adapter })).rejects.toBeTruthy()
    expect(auth.user).toBeNull()
  })

  it('notifies the configured global handler once when refresh fails', async () => {
    const auth = useAuthStore()
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('refresh failed'))
    const adapter = vi.fn(async (config) => {
      const error = new Error('Unauthorized')
      error.config = config
      error.response = { status: 401 }
      throw error
    })

    installAuthInterceptors(auth)
    await Promise.allSettled([api.get('/one', { adapter }), api.get('/two', { adapter })])

    expect(unauthorized).toHaveBeenCalledTimes(1)
    expect(auth.user).toBeNull()
  })
})
