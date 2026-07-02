import { describe, expect, it, vi } from 'vitest'

import { bootstrapApp } from './bootstrap'

describe('app bootstrap', () => {
  it('restores the session before installing navigation and mounting', async () => {
    let finishRestore
    const restore = vi.fn(() => new Promise((resolve) => { finishRestore = resolve }))
    const mount = vi.fn()
    const use = vi.fn()
    const isReady = vi.fn().mockResolvedValue()

    const pendingBootstrap = bootstrapApp(
      { mount, use },
      { restore },
      { isReady },
      { installGuards: vi.fn(), setUnauthorizedHandler: vi.fn() },
    )

    expect(restore).toHaveBeenCalledTimes(1)
    expect(use).not.toHaveBeenCalled()
    expect(mount).not.toHaveBeenCalled()

    finishRestore(true)
    await pendingBootstrap

    expect(use).toHaveBeenCalled()
    expect(isReady).toHaveBeenCalled()
    expect(mount).toHaveBeenCalledWith('#app')
  })

  it('configures session expiry navigation without coupling the API to the router', async () => {
    const push = vi.fn()
    const setUnauthorizedHandler = vi.fn()
    await bootstrapApp(
      { mount: vi.fn(), use: vi.fn() },
      { restore: vi.fn().mockResolvedValue(true) },
      { isReady: vi.fn().mockResolvedValue(), push, currentRoute: { value: { path: '/targets' } } },
      { installGuards: vi.fn(), setUnauthorizedHandler },
    )

    const handler = setUnauthorizedHandler.mock.calls[0][0]
    await handler()
    expect(push).toHaveBeenCalledWith({ path: '/login', query: { expired: '1' } })
  })
})
