import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useReconStore } from './recon'
import { useWebAuditStore } from './webaudit'

describe('scan stores', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('parses optional recon ports and starts a scan', async () => {
    const client = { post: vi.fn().mockResolvedValue({ data: { task_id: 'r1', status: 'pending' } }) }
    const recon = useReconStore()
    const task = await recon.start(3, '80, 443 8080', client)
    expect(client.post).toHaveBeenCalledWith('/recon/scan', { target_id: 3, ports: [80, 443, 8080] })
    expect(task.task_id).toBe('r1')
  })

  it('starts web audit with target and URL', async () => {
    const client = { post: vi.fn().mockResolvedValue({ data: { task_id: 'w1', status: 'pending' } }) }
    const audit = useWebAuditStore()
    await audit.start(4, 'https://example.com', client)
    expect(client.post).toHaveBeenCalledWith('/webaudit/check', { target_id: 4, url: 'https://example.com' })
  })
})
