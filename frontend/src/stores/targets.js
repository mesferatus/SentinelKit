import { ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '../services/api'
import { localDateTimeToIso } from '../utils/localDateTime'

function errorMessage(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail[0]?.msg?.replace(/^Value error,\s*/i, '') || 'Confira os dados informados.'
  if (typeof detail === 'string') return detail
  if (error.response?.status === 403) return 'Você não tem autorização para esta ação.'
  if (error.response?.status === 422) return 'Confira os dados informados.'
  return 'Não foi possível concluir. Tente novamente.'
}

export function getTargetStatus(target, now = new Date()) {
  if (!target.active) return 'revoked'
  return new Date(target.expires_at) <= now ? 'expired' : 'active'
}

export const useTargetsStore = defineStore('targets', () => {
  const targets = ref([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')
  const pendingActions = ref({})
  const pendingPromises = new Map()

  function isTargetPending(id) {
    return Boolean(pendingActions.value[id])
  }

  function runTargetAction(id, action, operation) {
    if (pendingPromises.has(id)) return pendingPromises.get(id)
    pendingActions.value = { ...pendingActions.value, [id]: action }
    const promise = (async () => operation())()
      .finally(() => {
        pendingPromises.delete(id)
        const next = { ...pendingActions.value }
        delete next[id]
        pendingActions.value = next
      })
    pendingPromises.set(id, promise)
    return promise
  }

  function replaceTarget(updated) {
    const index = targets.value.findIndex((target) => target.id === updated.id)
    if (index === -1) targets.value.unshift(updated)
    else targets.value[index] = updated
  }

  async function fetchTargets(client = api) {
    loading.value = true
    error.value = ''
    try {
      targets.value = (await client.get('/targets')).data
    } catch (requestError) {
      error.value = errorMessage(requestError)
    } finally {
      loading.value = false
    }
  }

  async function createTarget(payload, client = api) {
    saving.value = true
    try {
      const data = (await client.post('/targets', { ...payload, expires_at: localDateTimeToIso(payload.expires_at) })).data
      replaceTarget(data)
      return data
    } catch (requestError) {
      throw new Error(errorMessage(requestError))
    } finally {
      saving.value = false
    }
  }

  function renewTarget(id, expiresAt, client = api) {
    return runTargetAction(id, 'renew', async () => {
      try {
        const data = (await client.patch(`/targets/${id}/renew`, { confirmed: true, expires_at: localDateTimeToIso(expiresAt) })).data
        replaceTarget(data)
        return data
      } catch (requestError) {
        throw new Error(errorMessage(requestError))
      }
    })
  }

  function revokeTarget(id, client = api) {
    return runTargetAction(id, 'revoke', async () => {
      try {
        const data = (await client.patch(`/targets/${id}/revoke`)).data
        replaceTarget(data)
        return data
      } catch (requestError) {
        throw new Error(errorMessage(requestError))
      }
    })
  }

  return { targets, loading, saving, error, pendingActions, isTargetPending, fetchTargets, createTarget, renewTarget, revokeTarget }
})
