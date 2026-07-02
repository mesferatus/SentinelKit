<script setup>
defineOptions({ name: 'AppShell' })

import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { logoutAndRedirect } from './appShellActions'
import SentinelLogo from './SentinelLogo.vue'

const open = ref(false)
const feedback = ref('')
const auth = useAuthStore()
const router = useRouter()

const closeMenu = () => { open.value = false }
const signOut = () => logoutAndRedirect(auth, router, (message) => { feedback.value = message })
</script>

<template>
  <div class="app-frame">
    <header class="mobile-header">
      <RouterLink to="/" class="brand" @click="closeMenu"><SentinelLogo /></RouterLink>
      <button
        class="icon-button"
        type="button"
        :aria-expanded="open"
        :aria-label="open ? 'Fechar menu' : 'Abrir menu'"
        @click="open = !open"
      >☰</button>
    </header>

    <aside class="sidebar" :class="{ 'sidebar--open': open }">
      <RouterLink to="/" class="brand brand--desktop" aria-label="SentinelKit" @click="closeMenu">
        <SentinelLogo compact />
      </RouterLink>
      <nav aria-label="Navegação principal">
        <RouterLink to="/" class="nav-link" aria-label="Início" @click="closeMenu"><span>⌂</span><b>Início</b></RouterLink>
        <RouterLink to="/targets" class="nav-link" aria-label="Alvos" @click="closeMenu"><span>◎</span><b>Alvos</b></RouterLink>
        <RouterLink to="/recon" class="nav-link" aria-label="Recon" @click="closeMenu"><span>⌁</span><b>Recon</b></RouterLink>
        <RouterLink to="/webaudit" class="nav-link" aria-label="Web Audit" @click="closeMenu"><span>✓</span><b>Web Audit</b></RouterLink>
        <RouterLink to="/siem" class="nav-link" aria-label="SIEM" @click="closeMenu"><span>!</span><b>SIEM</b></RouterLink>
        <RouterLink to="/audit-logs" class="nav-link" aria-label="Logs de auditoria" @click="closeMenu"><span>≡</span><b>Logs</b></RouterLink>
      </nav>
      <button class="nav-link nav-link--logout" type="button" aria-label="Sair" @click="signOut">
        <span>↪</span><b>Sair</b>
      </button>
    </aside>

    <p v-if="feedback" class="sr-only" role="status">{{ feedback }}</p>
    <section class="app-main">
      <header class="topbar">
        <div class="topbar__brand">
          <SentinelLogo />
        </div>
        <label class="topbar__search">
          <span aria-hidden="true">⌕</span>
          <input type="search" placeholder="Buscar algo..." aria-label="Buscar algo">
        </label>
        <div class="topbar__actions">
          <RouterLink class="topbar__profile" to="/profile" aria-label="Editar perfil">
            <span class="topbar__avatar" aria-hidden="true">👩</span>
            <strong>{{ auth.user?.name?.split(' ')[0] || 'Sofia' }}</strong>
            <span aria-hidden="true">⌄</span>
          </RouterLink>
        </div>
      </header>
      <main class="app-content"><slot /></main>
    </section>
  </div>
</template>
