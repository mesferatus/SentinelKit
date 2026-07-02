<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import SentinelLogo from './SentinelLogo.vue'

const props = defineProps({ mode: { type: String, required: true } })
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const isLogin = props.mode === 'login'
const name = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const acceptedTerms = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (!isLogin && password.value !== confirmPassword.value) {
    error.value = 'As senhas precisam ser iguais.'
    return
  }
  try {
    const payload = isLogin
      ? { email: email.value, password: password.value }
      : { name: name.value, email: email.value, password: password.value, accepted_terms: acceptedTerms.value }
    await auth[isLogin ? 'login' : 'register'](payload)
    router.push(route.query.redirect || '/')
  } catch (caught) {
    error.value = caught.message
  }
}
</script>

<template>
  <main class="auth-page" :class="{ 'auth-page--register': !isLogin }">
    <div class="auth-shell">
      <section class="auth-story" aria-label="SentinelKit">
        <div class="auth-story__brand">
          <SentinelLogo />
        </div>

        <div class="auth-story__copy">
          <p class="auth-story__eyebrow">{{ isLogin ? 'Acesso seguro' : 'Primeiro acesso' }}</p>
          <h2>{{ isLogin ? 'Bem-vinda de volta!' : 'Vamos montar seu laboratório.' }}</h2>
          <p>
            {{ isLogin
              ? 'Entre para cuidar dos seus alvos autorizados com uma visão clara e local.'
              : 'Crie sua conta para cadastrar alvos autorizados e acompanhar as análises.' }}
          </p>
          <div class="auth-story__notes" aria-label="Diferenciais do SentinelKit">
            <span>Local</span>
            <span>Autorizado</span>
            <span>Leve</span>
          </div>
        </div>
        <span class="auth-shape auth-shape--one" aria-hidden="true"></span>
        <span class="auth-shape auth-shape--two" aria-hidden="true"></span>
        <span class="auth-shape auth-shape--three" aria-hidden="true"></span>
      </section>

      <section class="auth-card">
        <SentinelLogo compact />
        <h1>{{ isLogin ? 'Entrar' : 'Criar conta' }}</h1>
        <p class="auth-card__intro">
          {{ isLogin ? 'Sua área de segurança está pronta para você.' : 'Só falta uma conta para salvar seu espaço local.' }}
        </p>

        <form @submit.prevent="submit">
          <template v-if="!isLogin">
            <label for="name">Nome completo</label>
            <input id="name" v-model="name" autocomplete="name" minlength="2" required placeholder="Como podemos chamar você?">
          </template>

          <label for="email">E-mail</label>
          <input id="email" v-model="email" type="email" autocomplete="email" required placeholder="voce@exemplo.com">

          <label for="password">Senha</label>
          <input
            id="password"
            v-model="password"
            type="password"
            :autocomplete="isLogin ? 'current-password' : 'new-password'"
            minlength="8"
            pattern="(?=.*\d).{8,}"
            required
          >

          <template v-if="!isLogin">
            <p class="field-help">Use ao menos 8 caracteres e 1 número.</p>
            <label for="confirm-password">Confirmar senha</label>
            <input id="confirm-password" v-model="confirmPassword" type="password" autocomplete="new-password" required>
            <label class="terms-field">
              <input v-model="acceptedTerms" type="checkbox" required>
              <span>Usarei o SentinelKit somente em sistemas próprios ou expressamente autorizados.</span>
            </label>
          </template>

          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button class="button button--primary button--full" type="submit" :disabled="auth.loading">
            {{ auth.loading ? 'Só um instante…' : isLogin ? 'Entrar' : 'Criar conta' }}
          </button>
        </form>

        <p class="auth-card__switch">
          {{ isLogin ? 'Ainda não tem conta?' : 'Já tem uma conta?' }}
          <RouterLink :to="isLogin ? '/register' : '/login'">{{ isLogin ? 'Criar agora' : 'Entrar' }}</RouterLink>
        </p>
      </section>
    </div>
  </main>
</template>
