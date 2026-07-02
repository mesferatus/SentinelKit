import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '../services/api'

export const useDashboardStore = defineStore('dashboard', () => {
  const data = ref({ scans: 0, web_score: null, alerts: 0, recent_activity: [] })
  const loading = ref(false)
  const error = ref('')
  const metrics = computed(() => ({ scans: data.value.scans, web_score: data.value.web_score, alerts: data.value.alerts }))
  const activities = computed(() => data.value.recent_activity.slice(0, 3))

  async function fetchDashboard(client = api) {
    loading.value = true
    error.value = ''
    try {
      data.value = (await client.get('/dashboard')).data
    } catch {
      data.value = { scans: 0, web_score: null, alerts: 0, recent_activity: [] }
      error.value = 'Não conseguimos carregar o resumo agora.'
    } finally {
      loading.value = false
    }
  }

  return { data, metrics, activities, loading, error, fetchDashboard }
})
