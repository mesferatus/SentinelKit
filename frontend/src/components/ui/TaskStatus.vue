<script setup>
const props = defineProps({ status: { type: String, required: true } })
const labels = {
  pending: 'Na fila',
  running: 'Em andamento',
  completed: 'Concluído',
  failed: 'Falhou',
  alert: 'Atenção',
  clear: 'Tudo certo',
  success: 'Sucesso',
  error: 'Erro',
}
</script>

<template>
  <span class="task-status" :class="`task-status--${status}`">{{ labels[props.status] || status }}</span>
</template>
