import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getTargetStatus, useTargetsStore } from './targets'

describe('targets store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('loads targets and derives active, expired and revoked states', async () => {
    const now = new Date('2026-06-21T12:00:00Z')
    expect(getTargetStatus({ active: true, expires_at: '2026-06-22T12:00:00Z' }, now)).toBe('active')
    expect(getTargetStatus({ active: true, expires_at: '2026-06-20T12:00:00Z' }, now)).toBe('expired')
    expect(getTargetStatus({ active: false, expires_at: '2026-06-22T12:00:00Z' }, now)).toBe('revoked')
  })

  it('creates a confirmed target using the backend payload', async () => {
    const created = { id: 1, target: 'example.com', active: true, expires_at: '2026-07-01T12:00:00Z' }
    const client = {
      post: vi.fn().mockResolvedValue({ data: created }),
    }
    const store = useTargetsStore()

    await store.createTarget({
      target: 'example.com',
      evidence: 'Meu laboratório',
      confirmed: true,
      expires_at: '2026-07-01T12:00',
    }, client)

    expect(client.post).toHaveBeenCalledWith('/targets', {
      target: 'example.com',
      evidence: 'Meu laboratório',
      confirmed: true,
      expires_at: new Date('2026-07-01T12:00').toISOString(),
    })
    expect(store.targets[0]).toEqual(created)
  })

  it('renews and revokes a target', async () => {
    const store = useTargetsStore()
    store.targets = [{ id: 4, target: 'example.com', active: false, expires_at: '2026-06-20T12:00:00Z' }]
    const renewed = { ...store.targets[0], active: true, expires_at: '2026-07-10T12:00:00Z' }
    const revoked = { ...renewed, active: false }
    const client = {
      patch: vi.fn()
        .mockResolvedValueOnce({ data: renewed })
        .mockResolvedValueOnce({ data: revoked }),
    }

    await store.renewTarget(4, '2026-07-10T12:00', client)
    await store.revokeTarget(4, client)

    expect(client.patch).toHaveBeenNthCalledWith(1, '/targets/4/renew', {
      confirmed: true,
      expires_at: new Date('2026-07-10T12:00').toISOString(),
    })
    expect(client.patch).toHaveBeenNthCalledWith(2, '/targets/4/revoke')
    expect(store.targets[0].active).toBe(false)
  })

  it('translates 403 and validation errors into useful messages', async () => {
    const store = useTargetsStore()
    const forbidden = { response: { status: 403, data: { detail: 'Autorização do alvo expirou' } } }
    const invalid = { response: { status: 422, data: { detail: [{ msg: 'Value error, alvo inválido' }] } } }

    await expect(store.revokeTarget(1, { patch: vi.fn().mockRejectedValue(forbidden) }))
      .rejects.toThrow('Autorização do alvo expirou')
    await expect(store.createTarget({ expires_at: '2026-07-01T12:00' }, { post: vi.fn().mockRejectedValue(invalid) }))
      .rejects.toThrow('alvo inválido')
  })

  it('tracks pending actions per target and ignores duplicate operations', async () => {
    let finish
    const client = { patch: vi.fn(() => new Promise((resolve) => { finish = resolve })) }
    const store = useTargetsStore()

    const first = store.revokeTarget(9, client)
    const duplicate = store.revokeTarget(9, client)

    expect(store.isTargetPending(9)).toBe(true)
    expect(client.patch).toHaveBeenCalledTimes(1)
    finish({ data: { id: 9, active: false } })
    await Promise.all([first, duplicate])
    expect(store.isTargetPending(9)).toBe(false)
  })
})
