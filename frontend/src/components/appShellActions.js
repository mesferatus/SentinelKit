export async function logoutAndRedirect(auth, router, notify = () => {}) {
  try {
    await auth.logout()
  } catch {
    notify('Sessão encerrada localmente.')
  } finally {
    await router.push({ name: 'login' })
  }
}
