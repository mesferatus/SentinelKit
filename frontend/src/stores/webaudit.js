import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'

export const useWebAuditStore = defineStore('webaudit', () => {
  const submitting = ref(false)
  async function start(targetId, url, client = api) {
    submitting.value = true
    try {
      return (await client.post('/webaudit/check', { target_id: Number(targetId), url: url.trim() })).data
    } finally { submitting.value = false }
  }
  return { submitting, start }
})
