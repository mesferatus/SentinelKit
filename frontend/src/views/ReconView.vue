<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import TaskStatus from '../components/ui/TaskStatus.vue'
import kitten from '../assets/sentinel-kitten-approved-v2.webp'
import { api } from '../services/api'
import { useReconStore } from '../stores/recon'
import { useTasksStore } from '../stores/tasks'

const targets = ref([])
const targetId = ref('')
const ports = ref('')
const loading = ref(true)
const pageError = ref('')
const recon = useReconStore()
const tasks = useTasksStore()
const openPorts = computed(() => tasks.task?.result?.ports?.filter((item) => item.open) || [])

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
    const created = await recon.start(targetId.value, ports.value)
    await tasks.watch(created.task_id)
  } catch (error) {
    pageError.value =
      error.response?.data?.detail || error.message || 'Não foi possível iniciar o reconhecimento.'
  }
}
</script>

<template>
  <AppShell>
    <header class="page-heading">
      <p class="section-kicker">Recon</p>
      <h1>Portas sob observação</h1>
      <p>Verifique somente um alvo autorizado e ativo.</p>
    </header>

    <div class="scan-layout">
      <form class="scan-form" @submit.prevent="submit">
        <h2>Novo reconhecimento</h2>
        <label for="recon-target">Alvo autorizado</label>
        <select id="recon-target" v-model="targetId" required :disabled="loading || !targets.length">
          <option disabled value="">Selecione</option>
          <option v-for="target in targets" :key="target.id" :value="target.id">{{ target.target }}</option>
        </select>
        <label for="recon-ports">Portas opcionais</label>
        <input id="recon-ports" v-model="ports" placeholder="80, 443, 8080" inputmode="numeric">
        <p class="field-help">Vazio usa a lista segura padrão.</p>
        <button class="button button--primary" :disabled="!targetId || recon.submitting || tasks.polling">
          Iniciar reconhecimento
        </button>
      </form>

      <article class="result-panel" aria-live="polite">
        <p v-if="loading" class="page-message">Carregando alvos…</p>
        <p v-else-if="pageError || tasks.error" class="form-feedback" role="alert">
          {{ pageError || tasks.error }}
        </p>
        <div v-else-if="tasks.task">
          <div class="result-heading"><h2>Resultado</h2><TaskStatus :status="tasks.task.status" /></div>
          <p v-if="tasks.polling" class="page-message">O SentinelKit está conferindo as portas…</p>
          <template v-else-if="tasks.task.status === 'completed'">
            <p class="result-summary">{{ openPorts.length }} porta(s) aberta(s) · {{ tasks.task.result.duration_ms }} ms</p>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Porta</th><th>Banner</th></tr></thead>
                <tbody>
                  <tr v-for="item in openPorts" :key="item.port">
                    <td>{{ item.port }}</td><td>{{ item.banner || 'Sem banner' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-if="!openPorts.length" class="page-message">Nenhuma porta aberta encontrada.</p>
          </template>
        </div>
        <div v-else-if="!targets.length" class="recon-empty">
          <img :src="kitten" alt="Gatinho guardião do SentinelKit">
          <h2>Cadastre seu primeiro alvo</h2>
          <p>Adicione um ambiente próprio ou autorizado para liberar o reconhecimento de portas.</p>
          <RouterLink class="button button--primary" to="/targets">Cadastrar alvo autorizado</RouterLink>
        </div>
        <div v-else class="recon-empty recon-empty--compact">
          <img :src="kitten" alt="" aria-hidden="true">
          <h2>Pronto para observar</h2>
          <p>Escolha o alvo e inicie o reconhecimento. O resultado aparecerá aqui.</p>
        </div>
      </article>
    </div>
  </AppShell>
</template>
