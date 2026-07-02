import { render, screen, fireEvent, waitFor } from '@testing-library/vue'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'

import ProfileView from './ProfileView.vue'
import { useAuthStore } from '../stores/auth'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
}))

describe('ProfileView', () => {
  it('lets the user edit profile data', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.user = { id: 1, name: 'Sofia', email: 'sofia@example.com' }
    auth.updateProfile = vi.fn().mockResolvedValue({ id: 1, name: 'Sofia Lima' })
    render(ProfileView, { global: { plugins: [pinia] } })

    await fireEvent.update(screen.getByLabelText('Nome'), 'Sofia Lima')
    await fireEvent.update(screen.getByLabelText('E-mail'), 'sofia.lima@example.com')
    await fireEvent.click(screen.getByRole('button', { name: /salvar/i }))

    await waitFor(() => {
      expect(auth.updateProfile).toHaveBeenCalledWith({
        name: 'Sofia Lima',
        email: 'sofia.lima@example.com',
        password: null,
      })
    })
  })
})
