<script setup>
import { onMounted, reactive, ref } from 'vue'
import AppShell from '../components/AppShell.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { getTargetStatus, useTargetsStore } from '../stores/targets'
import { formatLocalDateTime } from '../utils/localDateTime'

const targetsStore = useTargetsStore()
const feedback = ref('')
const renewDates = reactive({})
const form = reactive({ target: '', evidence: '', expires_at: '', confirmed: false })
const labels = { active: 'Ativo', expired: 'Expirado', revoked: 'Revogado' }
const minimumDate = formatLocalDateTime(new Date(Date.now() + 60_000))

onMounted(() => targetsStore.fetchTargets())
const statusOf = (target) => getTargetStatus(target)
const formatDate = (value) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(value))

async function submit() {
  feedback.value = ''
  if (!form.confirmed) {
    feedback.value = 'Confirme sua autorização antes de adicionar o alvo.'
    return
  }
  try {
    await targetsStore.createTarget({ ...form })
    Object.assign(form, { target: '', evidence: '', expires_at: '', confirmed: false })
    feedback.value = 'Alvo autorizado adicionado.'
  } catch (error) {
    feedback.value = error.message
  }
}

async function renew(target) {
  feedback.value = ''
  if (!renewDates[target.id]) {
    feedback.value = 'Escolha uma nova validade futura.'
    return
  }
  try {
    await targetsStore.renewTarget(target.id, renewDates[target.id])
    renewDates[target.id] = ''
    feedback.value = 'Autorização renovada.'
  } catch (error) {
    feedback.value = error.message
  }
}

async function revoke(target) {
  feedback.value = ''
  try {
    await targetsStore.revokeTarget(target.id)
    feedback.value = 'Alvo revogado.'
  } catch (error) {
    feedback.value = error.message
  }
}
</script>

<template>
  <AppShell>
    <header class="page-heading">
      <p class="section-kicker">Autorização primeiro</p>
      <h1>Alvos autorizados</h1>
      <p>Cadastre apenas ambientes que você tem permissão para analisar.</p>
    </header>
    <p v-if="feedback" class="form-feedback" role="alert">{{ feedback }}</p>
    <p v-if="targetsStore.error" class="form-feedback" role="alert">{{ targetsStore.error }}</p>

    <section class="target-layout">
      <form class="target-form" aria-labelledby="new-target-title" @submit.prevent="submit">
        <h2 id="new-target-title">Adicionar alvo</h2>
        <label for="target">Alvo</label>
        <input id="target" v-model.trim="form.target" required maxlength="255" placeholder="exemplo.com">
        <label for="evidence">Evidência de autorização</label>
        <textarea id="evidence" v-model.trim="form.evidence" required maxlength="1000" placeholder="Ex.: meu servidor de laboratório" />
        <label for="expires-at">Validade da autorização</label>
        <input id="expires-at" v-model="form.expires_at" required type="datetime-local" :min="minimumDate">
        <label class="check-field">
          <input v-model="form.confirmed" type="checkbox">
          <span>Confirmo que tenho autorização para analisar este alvo.</span>
        </label>
        <button class="button button--primary" type="submit" :disabled="targetsStore.saving">Adicionar alvo</button>
      </form>

      <section class="targets-panel" aria-labelledby="targets-title">
        <h2 id="targets-title">Seus alvos</h2>
        <p v-if="targetsStore.loading" class="page-message" role="status">Carregando alvos…</p>
        <EmptyState v-else-if="!targetsStore.error && !targetsStore.targets.length" title="Nenhum alvo por aqui" description="Quando você adicionar um alvo autorizado, ele aparecerá nesta lista." />
        <ul v-else class="target-list">
          <li v-for="target in targetsStore.targets" :key="target.id" class="target-card">
            <div class="target-card__top">
              <div><strong>{{ target.target }}</strong><p>{{ target.evidence }}</p></div>
              <span class="target-status" :class="`target-status--${statusOf(target)}`">{{ labels[statusOf(target)] }}</span>
            </div>
            <p class="target-card__expiry">Válido até {{ formatDate(target.expires_at) }}</p>
            <div class="target-actions">
              <label :for="`renew-${target.id}`">Nova validade</label>
              <input :id="`renew-${target.id}`" v-model="renewDates[target.id]" type="datetime-local" :min="minimumDate">
              <button class="button button--soft" type="button" :disabled="targetsStore.isTargetPending(target.id)" @click="renew(target)">Renovar</button>
              <button class="button button--danger" type="button" :disabled="!target.active || targetsStore.isTargetPending(target.id)" @click="revoke(target)">Revogar</button>
            </div>
          </li>
        </ul>
      </section>
    </section>
  </AppShell>
</template>
