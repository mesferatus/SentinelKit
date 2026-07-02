<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import TaskStatus from '../components/ui/TaskStatus.vue'
import kitten from '../assets/sentinel-kitten-approved-v2.webp'
import { api } from '../services/api'
import { useTasksStore } from '../stores/tasks'
import { useWebAuditStore } from '../stores/webaudit'

const targets = ref([])
const targetId = ref('')
const url = ref('')
const loading = ref(true)
const pageError = ref('')
const audit = useWebAuditStore()
const tasks = useTasksStore()
const result = computed(() => tasks.task?.result)

onMounted(async () => {
  try {
    targets.value = (await api.get('/targets')).data.filter(
      (item) => item.active && new Date(item.expires_at) > new Date(),
    )
    targetId.value = targets.value[0]?.id || ''
  } catch {
    pageError.value = 'Não foi possível carregar seus alvos.'
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(tasks.cancel)

async function submit() {
  pageError.value = ''
  try {
    const created = await audit.start(targetId.value, url.value)
    await tasks.watch(created.task_id)
  } catch (error) {
    pageError.value =
      error.response?.data?.detail || error.message || 'Não foi possível iniciar a auditoria.'
  }
}
</script>

<template>
  <AppShell>
    <header class="page-heading">
      <p class="section-kicker">Web Audit</p>
      <h1>Checklist da aplicação</h1>
      <p>Headers, cookies e TLS em uma leitura tranquila.</p>
    </header>

    <div class="scan-layout">
      <form class="scan-form" @submit.prevent="submit">
        <h2>Nova auditoria</h2>
        <label for="audit-target">Alvo autorizado</label>
        <select id="audit-target" v-model="targetId" required :disabled="loading || !targets.length">
          <option disabled value="">Selecione</option>
          <option v-for="target in targets" :key="target.id" :value="target.id">{{ target.target }}</option>
        </select>
        <label for="audit-url">URL para auditoria</label>
        <input id="audit-url" v-model="url" type="url" placeholder="https://example.com" required>
        <button class="button button--primary" :disabled="!targetId || !url || audit.submitting || tasks.polling">
          Iniciar auditoria
        </button>
      </form>

      <article class="result-panel" aria-live="polite">
        <p v-if="loading" class="page-message">Carregando alvos…</p>
        <p v-else-if="pageError || tasks.error" class="form-feedback" role="alert">
          {{ pageError || tasks.error }}
        </p>
        <div v-else-if="tasks.task">
          <div class="result-heading"><h2>Resultado</h2><TaskStatus :status="tasks.task.status" /></div>
          <p v-if="tasks.polling" class="page-message">O SentinelKit está conferindo os detalhes…</p>
          <div v-else-if="result" class="audit-results">
            <div class="score-card">
              <strong>{{ result.score }}</strong><span>/ 100</span>
              <progress :value="result.score" max="100">{{ result.score }}</progress>
            </div>
            <section><h3>Headers</h3><ul class="check-list"><li v-for="(info, name) in result.headers" :key="name"><span>{{ name.replaceAll('_', ' ') }}</span><b>{{ info.present ? 'Presente' : 'Ausente' }}</b></li></ul></section>
            <section><h3>Cookies</h3><p v-if="!result.cookies?.length">Nenhum cookie retornado.</p><ul v-else class="check-list"><li v-for="cookie in result.cookies" :key="cookie.name"><span>{{ cookie.name }}</span><b>{{ cookie.secure && cookie.http_only ? 'Protegido' : 'Revisar' }}</b></li></ul></section>
            <section><h3>TLS</h3><p v-if="result.tls">{{ result.tls.protocol || 'Protocolo não informado' }} · {{ result.tls.issuer || 'Emissor não informado' }}</p><p v-else>Não se aplica à conexão HTTP.</p></section>
            <section><h3>Recomendações</h3><ul><li v-for="item in result.recommendations" :key="item">{{ item }}</li></ul><p v-if="!result.recommendations?.length">Tudo certinho por aqui.</p></section>
          </div>
        </div>
        <div v-else-if="!targets.length" class="recon-empty">
          <img :src="kitten" alt="Gatinho guardião do SentinelKit">
          <h2>Autorize um site primeiro</h2>
          <p>Cadastre o domínio que você possui ou tem permissão expressa para auditar.</p>
          <RouterLink class="button button--primary" to="/targets">Cadastrar alvo autorizado</RouterLink>
        </div>
        <div v-else class="recon-empty recon-empty--compact">
          <img :src="kitten" alt="" aria-hidden="true">
          <h2>Checklist pronto</h2>
          <p>Escolha o alvo e informe a URL. O relatório de segurança aparecerá aqui.</p>
        </div>
      </article>
    </div>
  </AppShell>
</template>
