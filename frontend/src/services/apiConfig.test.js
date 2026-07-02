import { describe, expect, it, vi } from 'vitest'

describe('desktop API configuration', () => {
  it('prefers the Electron-injected API URL', async () => {
    vi.resetModules()
    window.sentinelConfig = { apiUrl: 'http://127.0.0.1:9123' }
    const { api } = await import('./api')
    expect(api.defaults.baseURL).toBe('http://127.0.0.1:9123')
    delete window.sentinelConfig
  })
})
