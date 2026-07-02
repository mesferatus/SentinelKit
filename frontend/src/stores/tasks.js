import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'

const pause = (ms, signal) => new Promise((resolve) => {
  const timer = setTimeout(resolve, ms)
  signal.wake = () => { clearTimeout(timer); resolve() }
})

export const useTasksStore = defineStore('tasks', () => {
  const task = ref(null)
  const error = ref('')
  const polling = ref(false)
  let control = null

  function cancel() {
    if (!control) return
    const current = control
    current.cancelled = true
    current.controller.abort()
    current.wake?.()
    if (control === current) {
      control = null
      polling.value = false
    }
  }

  async function watch(taskId, client = api, { intervalMs = 2000, timeoutMs = 120000 } = {}) {
    cancel()
    const current = {
      cancelled: false,
      wake: null,
      controller: new AbortController(),
    }
    control = current
    polling.value = true
    error.value = ''
    task.value = { task_id: taskId, status: 'pending' }
    let latestTask = task.value
    const deadline = Date.now() + timeoutMs

    while (!current.cancelled) {
      try {
        const response = await client.get(`/tasks/${taskId}`, {
          signal: current.controller.signal,
        })
        if (control !== current) break
        latestTask = response.data
        task.value = latestTask
      } catch (requestError) {
        if (control !== current || current.controller.signal.aborted) break
        error.value = requestError.response?.data?.detail || 'Não foi possível acompanhar a tarefa.'
        break
      }
      if (latestTask.status === 'completed') break
      if (latestTask.status === 'failed') {
        if (control === current) error.value = latestTask.error || 'A tarefa falhou.'
        break
      }
      if (Date.now() >= deadline) {
        if (control === current) error.value = 'A tarefa atingiu o tempo limite.'
        break
      }
      await pause(Math.min(intervalMs, deadline - Date.now()), current)
    }

    if (control === current) {
      control = null
      polling.value = false
    }
    return latestTask
  }

  return { task, error, polling, watch, cancel }
})
