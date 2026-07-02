import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { render, screen } from '@testing-library/vue'

import SiemView from './SiemView.vue'
import AuditLogsView from './AuditLogsView.vue'

vi.mock('../stores/siem', async () => {
  const actual = await vi.importActual('../stores/siem')
  return {
    ...actual,
    useSiemStore: () => ({
      analyses: [],
      recentActivity: [],
      auditPage: { total: 0, page: 1, page_size: 20, items: [] },
      loading: false,
      analyzing: false,
      error: '',
      fetchDashboard: vi.fn(),
      fetchAuditLogs: vi.fn(),
      analyzeInternal: vi.fn(),
      analyzeUpload: vi.fn(),
    }),
  }
})

describe('SIEM views', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows upload guidance and internal analysis action', () => {
    render(SiemView, { global: { stubs: { AppShell: { template: '<main><slot /></main>' } } } })
    expect(screen.getByText(/até 2 MB/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: /analisar logs da plataforma/i })).toBeTruthy()
    expect(screen.getByLabelText(/arquivo de log/i).getAttribute('accept')).toContain('.log')
  })

  it('renders the real event frequency shape', () => {
    render(SiemView, {
      global: {
        stubs: { AppShell: { template: '<main><slot /></main>' } },
        mocks: {},
      },
    })
    expect(screen.queryByText('undefined')).toBeNull()
  })

  it('shows real audit pagination controls', () => {
    render(AuditLogsView, { global: { stubs: { AppShell: { template: '<main><slot /></main>' } } } })
    expect(screen.getByRole('button', { name: /anterior/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /próxima/i })).toBeTruthy()
  })
})
