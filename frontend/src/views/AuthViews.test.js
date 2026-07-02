import { fireEvent, render, screen } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'

import LoginView from './LoginView.vue'
import RegisterView from './RegisterView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

describe('auth views', () => {
  it('shows the branded login panel and submits login credentials', async () => {
    render(LoginView, { global: { plugins: [createPinia()] } })
    expect(screen.queryByRole('img', { name: /gatinho guardião branco e cinza/i })).toBeNull()
    expect(screen.getByRole('heading', { name: 'Bem-vinda de volta!' })).toBeTruthy()
    await fireEvent.update(screen.getByLabelText('E-mail'), 'sofia@example.com')
    await fireEvent.update(screen.getByLabelText('Senha'), 'Segura123')
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeTruthy()
  })

  it('shows the full registration form and password requirements', () => {
    render(RegisterView, { global: { plugins: [createPinia()] } })
    expect(screen.queryByRole('img', { name: /gatinho guardião branco e cinza/i })).toBeNull()
    expect(screen.getByRole('heading', { name: 'Vamos montar seu laboratório.' })).toBeTruthy()
    expect(screen.getByLabelText('Nome completo')).toBeTruthy()
    expect(screen.getByText(/8 caracteres e 1 número/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Criar conta' })).toBeTruthy()
    const password = screen.getByLabelText('Senha')
    expect(password.getAttribute('minlength')).toBe('8')
    expect(password.getAttribute('pattern')).toBe('(?=.*\\d).{8,}')
  })
})
