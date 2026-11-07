<script setup lang="ts">
import type { WorldLinkStatus } from "@/features/agents/utils/evaluateWorldLink";

defineProps<{
  status: WorldLinkStatus;
  reason: string;
}>();
</script>

<template>
  <div
    class="rounded-xl border px-3 py-2 text-xs text-base-content/80"
    :class="{
      'border-error/40 bg-error/10': status === 'red',
      'border-warning/40 bg-warning/10': status === 'yellow',
      'border-success/40 bg-success/10': status === 'green',
      'border-base-300 bg-base-200/50': status === 'off',
    }"
    :title="status"
  >
    <p>{{ reason }}</p>
  </div>
</template>
