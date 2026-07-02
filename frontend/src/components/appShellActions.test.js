import { describe, expect, it, vi } from 'vitest'

import { logoutAndRedirect } from './appShellActions'

describe('app shell actions', () => {
  it('always redirects to login when logout API fails', async () => {
    const logout = vi.fn().mockRejectedValue(new Error('API offline'))
    const push = vi.fn()
    const notify = vi.fn()

    await logoutAndRedirect({ logout }, { push }, notify)

    expect(push).toHaveBeenCalledWith({ name: 'login' })
    expect(notify).toHaveBeenCalledWith('Sessão encerrada localmente.')
  })
})
