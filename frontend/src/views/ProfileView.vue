<script setup>
import { reactive, ref, watchEffect } from 'vue'
import { useAuthStore } from '../stores/auth'
import AppShell from '../components/AppShell.vue'

const auth = useAuthStore()
const feedback = ref('')
const error = ref('')

const form = reactive({
  name: '',
  email: '',
  password: '',
})

watchEffect(() => {
  form.name = auth.user?.name || ''
  form.email = auth.user?.email || ''
})

async function saveProfile() {
  feedback.value = ''
  error.value = ''

  try {
    await auth.updateProfile({
      name: form.name,
      email: form.email,
      password: form.password || null,
    })
    form.password = ''
    feedback.value = 'Perfil atualizado.'
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <AppShell>
    <section class="profile-page" aria-labelledby="profile-title">
      <div class="profile-hero">
        <p class="section-kicker">Perfil</p>
        <h1 id="profile-title">Sua conta SentinelKit</h1>
        <p>Atualize seus dados sem sair do aplicativo.</p>
      </div>

      <form class="profile-card" @submit.prevent="saveProfile">
        <div class="profile-card__header">
          <span class="profile-card__avatar" aria-hidden="true">👩</span>
          <div>
            <h2>{{ auth.user?.name || 'Seu perfil' }}</h2>
            <p>{{ auth.user?.email || 'E-mail não informado' }}</p>
          </div>
        </div>

        <label>
          Nome
          <input v-model="form.name" type="text" autocomplete="name" required>
        </label>

        <label>
          E-mail
          <input v-model="form.email" type="email" autocomplete="email" required>
        </label>

        <label>
          Nova senha <span>opcional</span>
          <input v-model="form.password" type="password" autocomplete="new-password" placeholder="Mínimo 8 caracteres e 1 número">
        </label>

        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <p v-if="feedback" class="form-success" role="status">{{ feedback }}</p>

        <button class="button button--primary button--full" type="submit" :disabled="auth.loading">
          {{ auth.loading ? 'Salvando...' : 'Salvar alterações' }}
        </button>
      </form>
    </section>
  </AppShell>
</template>
