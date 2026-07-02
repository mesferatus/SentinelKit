import axios from 'axios'

export const api = axios.create({
  baseURL: window.sentinelConfig?.apiUrl || import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true,
  timeout: 8000,
})

let responseInterceptor
let refreshPromise = null
let unauthorizedHandler = () => {}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = typeof handler === 'function' ? handler : () => {}
}

export function installAuthInterceptors(authStore) {
  if (responseInterceptor !== undefined) api.interceptors.response.eject(responseInterceptor)

  responseInterceptor = api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config
      const isUnauthorized = error.response?.status === 401
      const isAuthRequest = original?.url?.includes('/auth/')

      if (!isUnauthorized || isAuthRequest || original?._retried) {
        return Promise.reject(error)
      }

      original._retried = true
      if (!refreshPromise) {
        refreshPromise = axios
          .post(`${api.defaults.baseURL}/auth/refresh`, null, { withCredentials: true })
          .then(({ data }) => {
            authStore.user = data.user
          })
          .catch((refreshError) => {
            authStore.clearSession()
            unauthorizedHandler()
            throw refreshError
          })
          .finally(() => {
            refreshPromise = null
          })
      }

      await refreshPromise
      return api(original)
    },
  )
}
