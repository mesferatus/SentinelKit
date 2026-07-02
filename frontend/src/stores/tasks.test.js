import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useTasksStore } from './tasks'

describe('tasks store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  it('polls every two seconds until completion', async () => {
    const client = { get: vi.fn()
      .mockResolvedValueOnce({ data: { status: 'running', result: null } })
      .mockResolvedValueOnce({ data: { status: 'completed', result: { score: 90 } } }) }
    const store = useTasksStore()
    const promise = store.watch('abc', client)
    await vi.advanceTimersByTimeAsync(2000)
    await promise

    expect(client.get).toHaveBeenCalledTimes(2)
    expect(store.task.result.score).toBe(90)
  })

  it('stops polling on failure, timeout and cancellation', async () => {
    const failedClient = { get: vi.fn().mockResolvedValue({ data: { status: 'failed', error: 'Falhou' } }) }
    const store = useTasksStore()
    await store.watch('failed', failedClient)
    expect(store.error).toBe('Falhou')

    const pendingClient = { get: vi.fn().mockResolvedValue({ data: { status: 'running' } }) }
    const timeoutPromise = store.watch('slow', pendingClient, { timeoutMs: 0 })
    await vi.runAllTimersAsync()
    await timeoutPromise
    expect(store.error).toMatch(/tempo limite/i)

    const cancelPromise = store.watch('cancel', pendingClient)
    await Promise.resolve()
    store.cancel()
    await cancelPromise
    expect(vi.getTimerCount()).toBe(0)
  })

  it('does not let an older late response overwrite a newer watch', async () => {
    let resolveOld
    const oldRequest = new Promise((resolve) => { resolveOld = resolve })
    const client = {
      get: vi.fn()
        .mockReturnValueOnce(oldRequest)
        .mockResolvedValueOnce({ data: { task_id: 'new', status: 'completed', result: { value: 'new' } } }),
    }
    const store = useTasksStore()
    const oldWatch = store.watch('old', client)
    const newWatch = store.watch('new', client)
    await newWatch
    resolveOld({ data: { task_id: 'old', status: 'completed', result: { value: 'old' } } })
    await oldWatch

    expect(store.task.task_id).toBe('new')
    expect(store.task.result.value).toBe('new')
    expect(store.polling).toBe(false)
  })

  it('passes an AbortSignal and aborts it when cancelled', async () => {
    let receivedSignal
    const client = {
      get: vi.fn((_url, config) => {
        receivedSignal = config.signal
        return new Promise((_resolve, reject) => {
          config.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        })
      }),
    }
    const store = useTasksStore()
    const watching = store.watch('cancel-me', client)
    await Promise.resolve()
    store.cancel()
    await watching

    expect(receivedSignal).toBeInstanceOf(AbortSignal)
    expect(receivedSignal.aborted).toBe(true)
    expect(store.error).toBe('')
    expect(store.polling).toBe(false)
  })
})
