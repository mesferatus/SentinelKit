import { render, screen, waitFor } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'

import DashboardView from './DashboardView.vue'
import { api } from '../services/api'

vi.mock('../services/api', () => ({ api: { get: vi.fn() } }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  RouterLink: { template: '<a><slot /></a>' },
}))

describe('DashboardView', () => {
  it('shows exactly three metrics and at most three activities', async () => {
    api.get.mockResolvedValue({
      data: {
        scans: 8,
        web_score: 88,
        alerts: 1,
        recent_activity: [
          { type: 'scan', title: 'Primeira', status: 'completed', timestamp: '2026-06-21T12:00:00Z' },
          { type: 'audit', title: 'Segunda', status: 'success', timestamp: '2026-06-21T11:00:00Z' },
          { type: 'siem', title: 'Terceira', status: 'alert', timestamp: '2026-06-21T10:00:00Z' },
        ],
      },
    })

    render(DashboardView, { global: { plugins: [createPinia()] } })

    await waitFor(() => expect(screen.getByText('Primeira')).toBeTruthy())
    expect(screen.getByRole('img', { name: /gatinho guardião/i })).toBeTruthy()
    expect(screen.getAllByRole('group')).toHaveLength(3)
    expect(screen.getByRole('heading', { name: 'Olá, você!' })).toBeTruthy()
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
  })

  it('shows loading, empty and error states accessibly', async () => {
    let rejectRequest
    api.get.mockReturnValue(new Promise((_, reject) => { rejectRequest = reject }))
    render(DashboardView, { global: { plugins: [createPinia()] } })
    await waitFor(() => expect(screen.getByRole('status').textContent).toMatch(/carregando/i))
    rejectRequest(new Error('offline'))
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.queryByText('Tudo quietinho')).toBeNull()
  })
})
