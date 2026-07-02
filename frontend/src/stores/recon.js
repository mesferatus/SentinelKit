import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'

export function parsePorts(value) {
  if (!value.trim()) return undefined
  const ports = [...new Set(value.split(/[\s,;]+/).filter(Boolean).map(Number))]
  if (!ports.length || ports.some((port) => !Number.isInteger(port) || port < 1 || port > 65535)) {
    throw new Error('Use portas entre 1 e 65535, separadas por vírgula ou espaço.')
  }
  return ports
}

export const useReconStore = defineStore('recon', () => {
  const submitting = ref(false)
  async function start(targetId, portsText, client = api) {
    submitting.value = true
    try {
      const payload = { target_id: Number(targetId) }
      const ports = parsePorts(portsText)
      if (ports) payload.ports = ports
      return (await client.post('/recon/scan', payload)).data
    } finally { submitting.value = false }
  }
  return { submitting, start }
})
