<script setup lang="ts">
import type { ToolLibraryUsageRow } from "@/features/tools/utils/buildToolLibraryIndex";
import { instanceStatusBadge } from "@/features/tools/utils/toolInstanceCardMeta";

defineProps<{
  row: ToolLibraryUsageRow;
}>();

const emit = defineEmits<{
  openInstance: [];
}>();
</script>

<template>
  <article class="card border border-warning/40 bg-base-100 shadow-sm">
    <div class="card-body gap-2 p-4">
      <p class="text-xs font-medium uppercase tracking-wide text-warning">Неизвестный тип</p>
      <p class="font-mono text-xs text-base-content/60">{{ row.instance.toolId }}</p>
      <div>
        <p class="font-medium">{{ row.agentName }}</p>
        <p class="font-mono text-[10px] text-base-content/45">{{ row.agentSlug }}</p>
      </div>
      <p class="text-sm text-base-content/70">{{ row.instance.name }}</p>
      <div class="card-actions justify-between pt-1">
        <span class="badge badge-xs" :class="instanceStatusBadge(row.instance).class">
          {{ instanceStatusBadge(row.instance).label }}
        </span>
        <button type="button" class="btn btn-xs btn-ghost" @click="emit('openInstance')">
          Открыть
        </button>
      </div>
    </div>
  </article>
</template>
