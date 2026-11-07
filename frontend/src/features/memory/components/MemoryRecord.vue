<script setup lang="ts">
import { computed } from "vue";
import { formatMemoryValue } from "@/features/memory/utils/memoryCard";

const props = defineProps<{
  title: string;
  record: Record<string, unknown>;
}>();

const entries = computed(() => Object.entries(props.record));
</script>

<template>
  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">{{ title }}</p>
    <p v-if="entries.length === 0" class="mt-1 text-sm text-base-content/50">Пусто</p>
    <dl v-else class="mt-1 space-y-1.5">
      <div v-for="[key, value] in entries" :key="key" class="min-w-0">
        <dt class="font-mono text-[11px] text-base-content/50">{{ key }}</dt>
        <dd class="break-words font-mono text-xs whitespace-pre-wrap">{{ formatMemoryValue(value) }}</dd>
      </div>
    </dl>
  </div>
</template>
