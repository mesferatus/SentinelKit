export async function bootstrapApp(app, auth, router, { installGuards, setUnauthorizedHandler }) {
  await auth.restore()
  setUnauthorizedHandler?.(() => {
    if (router.currentRoute?.value?.path === '/login') return
    return router.push({ path: '/login', query: { expired: '1' } })
  })
  installGuards(router, auth)
  app.use(router)
  await router.isReady()
  app.mount('#app')
}
