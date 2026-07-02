import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ReconView from './ReconView.vue'
import WebAuditView from './WebAuditView.vue'
import { api } from '../services/api'

vi.mock('../services/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }))

describe('scan views', () => {
  const scanViewGlobal = {
    plugins: [createPinia()],
    stubs: {
      AppShell: { template: '<main><slot /></main>' },
      RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: [{ id: 2, target: 'example.com', active: true, expires_at: '2099-01-01T00:00:00Z' }] })
  })

  it('shows an illustrated action when recon has no authorized target', async () => {
    api.get.mockResolvedValueOnce({ data: [] })
    render(ReconView, {
      global: {
        plugins: [createPinia()],
        stubs: {
          AppShell: { template: '<main><slot /></main>' },
          RouterLink: { template: '<a href="/targets"><slot /></a>' },
        },
      },
    })
    expect(await screen.findByRole('img', { name: /gatinho guardião/i })).toBeTruthy()
    expect(screen.getByRole('link', { name: /cadastrar alvo autorizado/i }).getAttribute('href')).toBe('/targets')
  })

  it('renders recon open ports after polling completes', async () => {
    api.post.mockResolvedValue({ data: { task_id: 'r1', status: 'pending' } })
    api.get
      .mockResolvedValueOnce({ data: [{ id: 2, target: 'example.com', active: true, expires_at: '2099-01-01T00:00:00Z' }] })
      .mockResolvedValueOnce({ data: { status: 'completed', result: { duration_ms: 12.5, ports: [{ port: 443, open: true, banner: 'HTTPS' }] } } })
    render(ReconView, { global: scanViewGlobal })
    await screen.findByText('example.com')
    await fireEvent.click(screen.getByRole('button', { name: /iniciar reconhecimento/i }))
    expect(await screen.findByText('HTTPS')).toBeTruthy()
    expect(screen.getByText('443')).toBeTruthy()
  })

  it('renders web score, headers, cookies, TLS and recommendations', async () => {
    api.post.mockResolvedValue({ data: { task_id: 'w1', status: 'pending' } })
    api.get
      .mockResolvedValueOnce({ data: [{ id: 2, target: 'example.com', active: true, expires_at: '2099-01-01T00:00:00Z' }] })
      .mockResolvedValueOnce({ data: { status: 'completed', result: {
        score: 82,
        headers: { content_security_policy: { present: true, value: 'default-src self' } },
        cookies: [{ name: 'session', http_only: true, secure: true, same_site: 'Lax' }],
        tls: { valid: true, protocol: 'TLSv1.3', issuer: 'Kitten CA' },
        recommendations: ['Adicione HSTS.'],
      } } })
    render(WebAuditView, { global: scanViewGlobal })
    await screen.findByText('example.com')
    await fireEvent.update(screen.getByLabelText('URL para auditoria'), 'https://example.com')
    await fireEvent.click(screen.getByRole('button', { name: /iniciar auditoria/i }))
    await waitFor(() => expect(screen.getAllByText('82').length).toBeGreaterThan(0))
    expect(screen.getByText('session')).toBeTruthy()
    expect(screen.getByText(/TLSv1\.3/)).toBeTruthy()
    expect(screen.getByText('Adicione HSTS.')).toBeTruthy()
  })
})
