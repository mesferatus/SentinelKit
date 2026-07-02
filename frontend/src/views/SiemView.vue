<script setup>
import { onMounted, ref } from 'vue'
import AppShell from '../components/AppShell.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { eventFrequency, useSiemStore, validateLogFile } from '../stores/siem'
const siem = useSiemStore()
const file = ref(null)
const feedback = ref('')
onMounted(() => siem.fetchDashboard())
function chooseFile(event) { file.value = event.target.files?.[0] || null; feedback.value = validateLogFile(file.value) }
async function upload() { feedback.value = validateLogFile(file.value); if (feedback.value) return; try { await siem.analyzeUpload(file.value); feedback.value = 'Log analisado com sucesso.' } catch (e) { feedback.value = e.message } }
async function analyzePlatform() { try { await siem.analyzeInternal(); feedback.value = 'Atividade da plataforma analisada.' } catch (e) { feedback.value = e.message } }
const formatDate = (value) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
const eventCount = (item) => item.summary?.detections ?? item.events?.length ?? 0
</script>
<template>
  <AppShell>
    <header class="page-heading"><p class="section-kicker">Detecção gentil</p><h1>SIEM</h1><p>Analise logs sem transformar a tela numa central cheia de ruído.</p></header>
    <div class="siem-actions">
      <section class="upload-card"><h2>Enviar arquivo</h2><p>Arquivos .log ou .txt em UTF-8, até 2 MB.</p><label for="log-file">Arquivo de log</label><input id="log-file" type="file" accept=".log,.txt,text/plain,text/x-log" @change="chooseFile"><button class="button button--primary" type="button" :disabled="siem.analyzing || !file" @click="upload">Analisar arquivo</button></section>
      <section class="upload-card"><h2>Atividade da plataforma</h2><p>Procure padrões suspeitos nos registros internos do SentinelKit.</p><button class="button button--soft" type="button" :disabled="siem.analyzing" @click="analyzePlatform">Analisar logs da plataforma</button></section>
    </div>
    <p v-if="feedback" class="page-message" role="status">{{ feedback }}</p><p v-if="siem.error" class="form-feedback" role="alert">{{ siem.error }}</p>
    <section class="activity-panel"><h2>Análises recentes</h2><p v-if="siem.loading" class="page-message" role="status">Carregando análises…</p><EmptyState v-else-if="!siem.error && !siem.analyses.length" title="Nenhum alerta por aqui" description="Faça uma análise para ver os agrupamentos encontrados." /><div v-else class="table-wrap"><table><thead><tr><th>Origem</th><th>Data</th><th>Detecções</th></tr></thead><tbody><tr v-for="item in siem.analyses" :key="item.id"><td>{{ item.source }}</td><td>{{ formatDate(item.timestamp) }}</td><td>{{ eventCount(item) }}</td></tr></tbody></table></div></section>
    <section v-if="siem.latestAnalysis?.events?.length" class="activity-panel siem-events"><h2>Grupos detectados</h2><div class="table-wrap"><table><thead><tr><th>Tipo</th><th>IP</th><th>Severidade</th><th>Ocorrências</th></tr></thead><tbody><tr v-for="(event, index) in siem.latestAnalysis.events" :key="`${event.type}-${event.ip}-${index}`"><td>{{ event.type }}</td><td>{{ event.ip }}</td><td><span :class="`severity severity--${event.severity}`">{{ event.severity }}</span></td><td>{{ eventFrequency(event) }}</td></tr></tbody></table></div></section>
  </AppShell>
</template>
