<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useSiemStore } from '../stores/siem'
const siem = useSiemStore()
onMounted(() => siem.fetchAuditLogs(1))
const changePage = (page) => siem.fetchAuditLogs(page)
const formatDate = (value) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
</script>
<template>
  <AppShell>
    <header class="page-heading"><p class="section-kicker">Rastro da plataforma</p><h1>Logs de auditoria</h1><p>Atividades autenticadas vinculadas à sua conta.</p></header>
    <p v-if="siem.error" class="form-feedback" role="alert">{{ siem.error }}</p>
    <section class="activity-panel">
      <p v-if="siem.loading" class="page-message" role="status">Carregando registros…</p>
      <EmptyState v-else-if="!siem.error && !siem.auditPage.items.length" title="Sem registros recentes" description="As ações autenticadas aparecerão aqui." />
      <div v-else class="table-wrap"><table><thead><tr><th>Método</th><th>Endpoint</th><th>IP</th><th>Status</th><th>Data</th></tr></thead><tbody><tr v-for="item in siem.auditPage.items" :key="item.id"><td>{{ item.method }}</td><td>{{ item.endpoint }}</td><td>{{ item.source_ip }}</td><td>{{ item.status_code }}</td><td>{{ formatDate(item.timestamp) }}</td></tr></tbody></table></div>
      <nav class="pagination" aria-label="Paginação dos logs"><button class="button button--soft" type="button" :disabled="siem.loading || siem.auditPage.page <= 1" @click="changePage(siem.auditPage.page - 1)">Anterior</button><span>Página {{ siem.auditPage.page }}</span><button class="button button--soft" type="button" :disabled="siem.loading || siem.auditPage.page * siem.auditPage.page_size >= siem.auditPage.total" @click="changePage(siem.auditPage.page + 1)">Próxima</button></nav>
    </section>
  </AppShell>
</template>
