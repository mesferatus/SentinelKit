<script setup>
import mark from '../assets/sentinelkit-mark.svg'
defineProps({ compact: { type: Boolean, default: false } })
</script>
<template>
  <span class="sentinel-logo">
    <img :src="mark" alt="" aria-hidden="true">
    <span v-if="!compact">SentinelKit</span>
  </span>
</template>
