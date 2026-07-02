export function resolveAuthNavigation(meta, isAuthenticated, fullPath = '/') {
  if (meta.requiresAuth && !isAuthenticated) {
    return { name: 'login', query: { redirect: fullPath } }
  }
  if (meta.guestOnly && isAuthenticated) return { name: 'dashboard' }
  return true
}
