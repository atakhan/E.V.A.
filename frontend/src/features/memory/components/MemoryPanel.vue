<script setup lang="ts">
import { RouterLink } from "vue-router";
import MemoryReadout from "@/features/memory/components/MemoryReadout.vue";
import type { AgentMemory } from "@/features/runtime/types/runtime";
import { agentMemoryPath } from "@/router/paths";

defineProps<{
  agentSlug: string;
  memory: AgentMemory | null;
  loading: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <aside
    class="absolute inset-y-0 right-0 z-30 flex w-[22rem] flex-col border-l border-base-300/60 bg-base-100 shadow-xl sm:w-[28rem]"
    data-canvas-ui
  >
    <header class="flex items-start justify-between gap-2 border-b border-base-300 px-4 py-3">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-wide text-base-content/50">Память</p>
        <h2 class="mt-0.5 text-base font-semibold">История и рабочее состояние</h2>
      </div>
      <button
        type="button"
        class="btn btn-xs btn-square btn-ghost shrink-0"
        aria-label="Закрыть"
        @click="emit('close')"
      >
        ✕
      </button>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
      <MemoryReadout :agent-slug="agentSlug" :memory="memory" :loading="loading" :error="error" />
    </div>

    <footer class="border-t border-base-300 px-4 py-3">
      <RouterLink :to="agentMemoryPath(agentSlug)" class="btn btn-sm">Открыть раздел</RouterLink>
    </footer>
  </aside>
</template>
