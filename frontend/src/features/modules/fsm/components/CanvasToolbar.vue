<script setup lang="ts">
import type { CanvasTool } from "@/features/modules/fsm/types/canvas";

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
    aria-label="Инструменты"
  >
    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': activeTool === 'select' }"
      title="Выбор и перемещение"
      aria-label="Выбор и перемещение"
      @click="selectTool('select')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 4l8 18 2.5-7.5L22 12 4 4z" />
      </svg>
    </button>

    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': activeTool === 'rectangle' }"
      title="Прямоугольник"
      aria-label="Прямоугольник"
      @click="selectTool('rectangle')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="5" y="7" width="14" height="10" rx="1" />
      </svg>
    </button>
  </div>
</template>
