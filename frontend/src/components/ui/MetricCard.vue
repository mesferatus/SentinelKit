<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  suffix: { type: String, default: '' },
  hint: { type: String, default: '' },
  tone: { type: String, default: 'teal' },
  icon: { type: String, default: '◎' },
})

const ariaLabel = computed(() => `${props.label}: ${props.value}${props.suffix}`)
</script>

<template>
  <article class="metric-card" :class="`metric-card--${tone}`" role="group" :aria-label="ariaLabel">
    <div class="metric-card__icon" aria-hidden="true">{{ icon }}</div>
    <div>
      <p class="metric-card__label">{{ label }}</p>
      <p class="metric-card__value">{{ value }}<span>{{ suffix }}</span></p>
      <p v-if="hint" class="metric-card__hint">{{ hint }}</p>
    </div>
  </article>
</template>
