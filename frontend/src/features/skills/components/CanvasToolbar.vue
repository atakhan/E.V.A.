<script setup lang="ts">
import type { CanvasTool } from "@/features/skills/types/fsm";

defineProps<{
  activeTool: CanvasTool;
}>();

const emit = defineEmits<{
  "update:activeTool": [tool: CanvasTool];
}>();

function selectTool(tool: CanvasTool) {
  emit("update:activeTool", tool);
}
</script>

<template>
  <div
    class="absolute bottom-5 left-1/2 z-20 flex -translate-x-1/2 items-center gap-1 rounded-2xl border border-base-300/60 bg-base-100/90 p-1.5 shadow-lg backdrop-blur-sm"
    role="toolbar"
    aria-label="Инструменты FSM"
  >
    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': activeTool === 'select' }"
      title="Выбор"
      aria-label="Выбор"
      @click="selectTool('select')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 4l8 18 2.5-7.5L22 12 4 4z" />
      </svg>
    </button>

    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': activeTool === 'state' }"
      title="State"
      aria-label="State"
      @click="selectTool('state')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="5" y="7" width="14" height="10" rx="2" />
      </svg>
    </button>

    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': activeTool === 'transition' }"
      title="Transition"
      aria-label="Transition"
      @click="selectTool('transition')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 12h12" />
        <path d="M14 7l5 5-5 5" />
      </svg>
    </button>
  </div>
</template>
