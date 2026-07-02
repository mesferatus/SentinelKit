<script setup>
import { onMounted } from 'vue'
import AppShell from '../components/AppShell.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import MetricCard from '../components/ui/MetricCard.vue'
import TaskStatus from '../components/ui/TaskStatus.vue'
import kitten from '../assets/sentinel-kitten-approved-v2.webp'
import { useDashboardStore } from '../stores/dashboard'
import { useAuthStore } from '../stores/auth'

const dashboard = useDashboardStore()
const auth = useAuthStore()
onMounted(() => dashboard.fetchDashboard())

function formatDate(value) {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}
</script>

<template>
  <AppShell>
    <div class="dashboard-fixed">
      <section class="welcome">
        <div class="welcome__copy">
          <h1>Olá, {{ auth.user?.name?.split(' ')[0] || 'você' }}!</h1>
          <p>Tudo protegido por aqui.</p>
          <span aria-hidden="true"></span>
        </div>
        <img class="welcome__kitten" :src="kitten" alt="Gatinho guardião do SentinelKit">
      </section>

      <p v-if="dashboard.error" class="page-message" role="alert">{{ dashboard.error }}</p>
      <section id="metrics" class="metrics" aria-label="Resumo de segurança">
        <MetricCard label="Scans" :value="dashboard.metrics.scans" hint="Total realizado" tone="teal" icon="◎" />
        <MetricCard label="Score web" :value="dashboard.metrics.web_score ?? '—'" suffix="/100" hint="Média das auditorias" tone="yellow" icon="◉" />
        <MetricCard label="Alertas" :value="dashboard.metrics.alerts" hint="Detecções SIEM" tone="coral" icon="!" />
      </section>

      <section id="activity" class="activity-panel">
        <header>
          <div>
            <p class="section-kicker">Últimos acontecimentos</p>
            <h2>Atividade recente</h2>
          </div>
          <a class="activity-panel__link" href="#activity" aria-label="Ver todas as atividades">Ver todos ›</a>
        </header>
        <p v-if="dashboard.loading" class="page-message" role="status">Carregando com cuidado…</p>
        <EmptyState v-else-if="!dashboard.error && !dashboard.activities.length" title="Tudo quietinho" description="Suas três atividades mais recentes aparecerão aqui." />
        <ul v-else class="activity-list">
          <li v-for="item in dashboard.activities" :key="`${item.timestamp}-${item.title}`">
            <span class="activity-list__icon" aria-hidden="true">•</span>
            <div>
              <strong>{{ item.title }}</strong>
              <small>{{ item.type || 'atividade' }}</small>
            </div>
            <TaskStatus :status="item.status" />
            <time :datetime="item.timestamp">{{ formatDate(item.timestamp) }}</time>
          </li>
        </ul>
      </section>
    </div>
  </AppShell>
</template>
