import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useDashboardStore } from './dashboard'

describe('dashboard store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('loads only the dashboard contract returned by the API', async () => {
    const client = {
      get: vi.fn().mockResolvedValue({
        data: {
          scans: 7,
          web_score: 91.5,
          alerts: 2,
          recent_activity: [
            { type: 'scan', title: 'Recon: example.com', status: 'completed', timestamp: '2026-06-21T12:00:00Z' },
          ],
        },
      }),
    }
    const store = useDashboardStore()

    await store.fetchDashboard(client)

    expect(client.get).toHaveBeenCalledWith('/dashboard')
    expect(store.metrics).toEqual({ scans: 7, web_score: 91.5, alerts: 2 })
    expect(store.activities).toHaveLength(1)
    expect(store.loading).toBe(false)
  })

  it('exposes a friendly error when loading fails', async () => {
    const store = useDashboardStore()

    await store.fetchDashboard({ get: vi.fn().mockRejectedValue(new Error('offline')) })

    expect(store.error).toMatch(/carregar o resumo/i)
    expect(store.activities).toEqual([])
  })
})
