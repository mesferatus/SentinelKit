import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { MAX_LOG_BYTES, eventFrequency, validateLogFile, useSiemStore } from './siem'

describe('SIEM store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('rejects oversized and binary files before upload', () => {
    expect(validateLogFile(new File(['a'], 'access.exe', { type: 'application/octet-stream' }))).toMatch(/texto/i)
    expect(validateLogFile({ name: 'large.log', size: MAX_LOG_BYTES + 1, type: 'text/plain' })).toMatch(/2 MB/i)
  })

  it('loads dashboard and uploads logs with multipart source', async () => {
    const client = {
      get: vi.fn().mockResolvedValue({ data: { analyses: [{ id: 1 }], recent_activity: [{ id: 2 }] } }),
      post: vi.fn().mockResolvedValue({ data: { id: 3, events: [] } }),
    }
    const store = useSiemStore()
    await store.fetchDashboard(client)
    await store.analyzeUpload(new File(['line'], 'access.log', { type: 'text/plain' }), client)
    expect(store.analyses).toHaveLength(2)
    const body = client.post.mock.calls[0][1]
    expect(body.get('source')).toBe('upload')
    expect(body.get('file').name).toBe('access.log')
  })

  it('analyzes platform logs', async () => {
    const client = { post: vi.fn().mockResolvedValue({ data: { id: 4, events: [] } }) }
    const store = useSiemStore()
    await store.analyzeInternal(client)
    expect(client.post.mock.calls[0][1].get('source')).toBe('internal')
  })

  it('loads real paginated audit log response', async () => {
    const client = { get: vi.fn().mockResolvedValue({ data: { total: 21, page: 2, page_size: 20, items: [{ id: 21 }] } }) }
    const store = useSiemStore()
    await store.fetchAuditLogs(2, client)
    expect(client.get).toHaveBeenCalledWith('/audit-logs', { params: { page: 2, page_size: 20 } })
    expect(store.auditPage).toMatchObject({ total: 21, page: 2, page_size: 20 })
  })
})
  it('reads the real SIEM event frequency shape', () => {
    expect(eventFrequency({ type: 'sqli', ip: '198.51.100.7', severity: 'high', frequency: 4 })).toBe(4)
  })
