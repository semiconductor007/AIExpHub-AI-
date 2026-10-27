<script setup lang="ts">
withDefaults(defineProps<{ name: 'project' | 'batch' | 'experiment' | 'result' | 'compare' | 'chart'; size?: number }>(), { size: 24 })
const paths = {
  project: 'M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3Z',
  batch: 'm12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5',
  experiment: 'M9 3h6M10 3v6L4 19a1.3 1.3 0 0 0 1 2h14a1.3 1.3 0 0 0 1-2L14 9V3M8 14h8',
  result: 'M9 3H5v18h14V3h-4M9 2h6v4H9ZM8 13l3 3 5-6',
  compare: 'M5 20V10h4v10M10 20V4h4v16M15 20v-7h4v7M3 20h18',
  chart: 'M3 3v18h18M6 15l5-5 4 3 6-8',
}
</script>
<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name]" /></svg>
</template>
