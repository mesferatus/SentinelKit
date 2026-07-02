import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import { bootstrapApp } from './bootstrap'
import { installGuards, router } from './router'
import { installAuthInterceptors, setUnauthorizedHandler } from './services/api'
import { useAuthStore } from './stores/auth'
import './styles.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

const auth = useAuthStore()
installAuthInterceptors(auth)

bootstrapApp(app, auth, router, { installGuards, setUnauthorizedHandler })
