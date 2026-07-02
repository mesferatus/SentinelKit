import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '../services/api'

function errorMessage(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail[0]?.msg || 'Confira os dados informados.'
  return detail || 'Não foi possível concluir. Tente novamente.'
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value))

  function clearSession() {
    user.value = null
  }

  async function authenticate(endpoint, credentials, client = api) {
    loading.value = true
    try {
      const { data } = await client.post(endpoint, credentials)
      user.value = data.user
      return data
    } catch (error) {
      throw new Error(errorMessage(error))
    } finally {
      loading.value = false
    }
  }

  const login = (credentials, client) => authenticate('/auth/login', credentials, client)
  const register = (credentials, client) => authenticate('/auth/register', credentials, client)

  async function restore(client = api) {
    try {
      const { data } = await client.post('/auth/refresh')
      user.value = data.user
      return true
    } catch {
      clearSession()
      return false
    }
  }

  async function logout(client = api) {
    try {
      await client.post('/auth/logout')
    } finally {
      clearSession()
    }
  }

  async function updateProfile(payload, client = api) {
    loading.value = true
    try {
      const { data } = await client.patch('/auth/profile', payload)
      user.value = data
      return data
    } catch (error) {
      throw new Error(errorMessage(error))
    } finally {
      loading.value = false
    }
  }

  return {
    user,
    loading,
    isAuthenticated,
    clearSession,
    login,
    register,
    restore,
    logout,
    updateProfile,
  }
})
