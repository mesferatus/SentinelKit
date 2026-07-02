import { createRouter, createWebHistory } from 'vue-router'

import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import TargetsView from '../views/TargetsView.vue'
import ReconView from '../views/ReconView.vue'
import WebAuditView from '../views/WebAuditView.vue'
import SiemView from '../views/SiemView.vue'
import AuditLogsView from '../views/AuditLogsView.vue'
import ProfileView from '../views/ProfileView.vue'
import { useAuthStore } from '../stores/auth'
import { resolveAuthNavigation } from './guards'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/targets', name: 'targets', component: TargetsView, meta: { requiresAuth: true } },
    { path: '/recon', name: 'recon', component: ReconView, meta: { requiresAuth: true } },
    { path: '/webaudit', name: 'webaudit', component: WebAuditView, meta: { requiresAuth: true } },
    { path: '/siem', name: 'siem', component: SiemView, meta: { requiresAuth: true } },
    { path: '/audit-logs', name: 'audit-logs', component: AuditLogsView, meta: { requiresAuth: true } },
    { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: LoginView, meta: { guestOnly: true } },
    { path: '/register', name: 'register', component: RegisterView, meta: { guestOnly: true } },
  ],
})

export function installGuards(targetRouter = router, auth = useAuthStore()) {
  targetRouter.beforeEach((to) => resolveAuthNavigation(to.meta, auth.isAuthenticated, to.fullPath))
}
