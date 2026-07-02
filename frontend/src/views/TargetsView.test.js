import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import TargetsView from './TargetsView.vue'
import { api } from '../services/api'

vi.mock('../services/api', () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  RouterLink: { template: '<a><slot /></a>' },
}))

describe('TargetsView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('creates an authorized target from accessible fields', async () => {
    api.get.mockResolvedValue({ data: [] })
    api.post.mockResolvedValue({
      data: { id: 1, target: 'example.com', evidence: 'Meu lab', confirmed: true, active: true, expires_at: '2099-01-01T12:00:00Z' },
    })
    render(TargetsView, { global: { plugins: [createPinia()] } })
    await waitFor(() => expect(screen.getByText(/nenhum alvo/i)).toBeTruthy())

    await fireEvent.update(screen.getByLabelText('Alvo'), 'example.com')
    await fireEvent.update(screen.getByLabelText('Evidência de autorização'), 'Meu lab')
    await fireEvent.update(screen.getByLabelText('Validade da autorização'), '2099-01-01T12:00')
    await fireEvent.click(screen.getByLabelText(/confirmo que tenho autorização/i))
    await fireEvent.click(screen.getByRole('button', { name: 'Adicionar alvo' }))

    await waitFor(() => expect(api.post).toHaveBeenCalled())
    expect(screen.getByText('example.com')).toBeTruthy()
    expect(screen.getByText('Ativo')).toBeTruthy()
  })

  it('requires explicit authorization confirmation', async () => {
    api.get.mockResolvedValue({ data: [] })
    render(TargetsView, { global: { plugins: [createPinia()] } })
    await fireEvent.update(screen.getByLabelText('Alvo'), 'example.com')
    await fireEvent.update(screen.getByLabelText('Evidência de autorização'), 'Meu lab')
    await fireEvent.update(screen.getByLabelText('Validade da autorização'), '2099-01-01T12:00')
    await fireEvent.click(screen.getByRole('button', { name: 'Adicionar alvo' }))

    expect((await screen.findByRole('alert')).textContent).toMatch(/confirme sua autorização/i)
    expect(api.post).not.toHaveBeenCalled()
  })

  it('does not show the empty state when loading targets fails', async () => {
    api.get.mockRejectedValue({ response: { status: 403, data: { detail: 'Acesso negado' } } })
    render(TargetsView, { global: { plugins: [createPinia()] } })

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByText(/nenhum alvo/i)).toBeNull()
  })

  it('prevents duplicate actions for the same target while a request is pending', async () => {
    let finish
    api.get.mockResolvedValue({
      data: [{ id: 7, target: 'example.com', evidence: 'Lab', active: true, expires_at: '2099-01-01T12:00:00Z' }],
    })
    api.patch.mockReturnValue(new Promise((resolve) => { finish = resolve }))
    render(TargetsView, { global: { plugins: [createPinia()] } })
    await screen.findByText('example.com')

    const revoke = screen.getByRole('button', { name: 'Revogar' })
    await fireEvent.click(revoke)
    await fireEvent.click(revoke)

    expect(api.patch).toHaveBeenCalledTimes(1)
    expect(revoke.disabled).toBe(true)
    expect(screen.getByRole('button', { name: 'Renovar' }).disabled).toBe(true)
    finish({ data: { id: 7, target: 'example.com', evidence: 'Lab', active: false, expires_at: '2099-01-01T12:00:00Z' } })
  })
})
