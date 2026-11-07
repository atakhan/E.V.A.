<script setup lang="ts">
import type { SkillOrbitId } from "@/features/skills/utils/skillOrbit";

defineProps<{
  id: SkillOrbitId;
}>();
</script>

<template>
  <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
    <template v-if="id === 'about'">
      <circle cx="12" cy="8" r="3" />
      <path stroke-linecap="round" d="M5 19c1.5-4 4-6 7-6s5.5 2 7 6" />
    </template>
    <template v-else-if="id === 'states'">
      <rect x="4" y="4" width="7" height="7" rx="1.5" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" />
      <path stroke-linecap="round" d="M11 7.5h2.5M15.5 11v2.5" />
    </template>
    <template v-else>
      <circle cx="8" cy="12" r="2.5" />
      <circle cx="16" cy="8" r="2" />
      <circle cx="16" cy="16" r="2" />
      <path stroke-linecap="round" d="M10.2 10.8 14 9M10.2 13.2 14 15" />
    </template>
  </svg>
</template>
