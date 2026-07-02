import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../services/api'

export const MAX_LOG_BYTES = 2 * 1024 * 1024
export const eventFrequency = (event) => event.frequency ?? 0

export function validateLogFile(file) {
  if (!file) return 'Escolha um arquivo de log.'
  if (file.size > MAX_LOG_BYTES) return 'O arquivo deve ter no máximo 2 MB.'
  if (!/\.(log|txt)$/i.test(file.name || '') || !['', 'text/plain', 'text/x-log'].includes(file.type || '')) return 'Envie somente um arquivo de texto .log ou .txt.'
  return ''
}

export const useSiemStore = defineStore('siem', () => {
  const analyses = ref([])
  const recentActivity = ref([])
  const auditPage = ref({ total: 0, page: 1, page_size: 20, items: [] })
  const loading = ref(false)
  const analyzing = ref(false)
  const error = ref('')
  const latestAnalysis = computed(() => analyses.value[0] || null)
  const message = (err) => err.response?.data?.detail || 'Não foi possível concluir a análise agora.'

  async function fetchDashboard(client = api) {
    loading.value = true; error.value = ''
    try {
      const { data } = await client.get('/siem/dashboard')
      analyses.value = data.analyses || []; recentActivity.value = data.recent_activity || []
    } catch (err) { error.value = message(err) } finally { loading.value = false }
  }
  async function fetchAuditLogs(page = 1, client = api) {
    loading.value = true; error.value = ''
    try { auditPage.value = (await client.get('/audit-logs', { params: { page, page_size: 20 } })).data }
    catch (err) { error.value = message(err) }
    finally { loading.value = false }
  }
  async function submit(form, client) {
    analyzing.value = true; error.value = ''
    try {
      const { data } = await client.post('/siem/analyze', form)
      analyses.value = [data, ...analyses.value.filter((item) => item.id !== data.id)]
      return data
    } catch (err) { error.value = message(err); throw new Error(error.value) } finally { analyzing.value = false }
  }
  function analyzeInternal(client = api) {
    const form = new FormData(); form.append('source', 'internal'); return submit(form, client)
  }
  function analyzeUpload(file, client = api) {
    const invalid = validateLogFile(file)
    if (invalid) return Promise.reject(new Error(invalid))
    const form = new FormData(); form.append('source', 'upload'); form.append('file', file); return submit(form, client)
  }
  return { analyses, recentActivity, auditPage, latestAnalysis, loading, analyzing, error, fetchDashboard, fetchAuditLogs, analyzeInternal, analyzeUpload }
})
