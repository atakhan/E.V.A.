<script setup lang="ts">
import type { PluginOrbitId } from "@/features/tools/utils/pluginOrbit";

defineProps<{
  id: PluginOrbitId;
}>();
</script>

<template>
  <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
    <template v-if="id === 'about'">
      <circle cx="12" cy="8" r="3" />
      <path stroke-linecap="round" d="M5 19c1.5-4 4-6 7-6s5.5 2 7 6" />
    </template>
    <template v-else-if="id === 'commands'">
      <path stroke-linecap="round" d="M8 7h8M8 12h8M8 17h5" />
    </template>
    <template v-else-if="id === 'events'">
      <path stroke-linecap="round" stroke-linejoin="round" d="M13 3 4 14h7l-1 7 9-11h-7l1-7z" />
    </template>
    <template v-else-if="id === 'config'">
      <circle cx="12" cy="12" r="3" />
      <path
        stroke-linecap="round"
        d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"
      />
    </template>
    <template v-else-if="id === 'credential'">
      <path stroke-linecap="round" stroke-linejoin="round" d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z" />
    </template>
    <template v-else>
      <circle cx="8" cy="12" r="2.5" />
      <circle cx="16" cy="8" r="2" />
      <circle cx="16" cy="16" r="2" />
      <path stroke-linecap="round" d="M10.2 10.8 14 9M10.2 13.2 14 15" />
    </template>
  </svg>
</template>
