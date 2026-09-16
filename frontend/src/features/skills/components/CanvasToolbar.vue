<script setup lang="ts">
import type { CanvasTool, FlowDirection } from "@/features/skills/types/fsm";

const props = defineProps<{
  activeTool: CanvasTool;
  flowDirection?: FlowDirection;
}>();

const emit = defineEmits<{
  "update:activeTool": [tool: CanvasTool];
  "update:flowDirection": [direction: FlowDirection];
  autoLayout: [];
}>();

function selectTool(tool: CanvasTool) {
  emit("update:activeTool", tool);
}

const flow = () => props.flowDirection ?? "vertical";
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

    <span class="mx-1 h-6 w-px bg-base-300" aria-hidden="true" />

    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': flow() === 'vertical' }"
      title="Поток сверху вниз"
      aria-label="Поток сверху вниз"
      @click="emit('update:flowDirection', 'vertical')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 4v16" />
        <path d="M7 15l5 5 5-5" />
      </svg>
    </button>

    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': flow() === 'horizontal' }"
      title="Поток слева направо"
      aria-label="Поток слева направо"
      @click="emit('update:flowDirection', 'horizontal')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 12h16" />
        <path d="M15 7l5 5-5 5" />
      </svg>
    </button>

    <button
      type="button"
      class="btn btn-sm btn-square"
      title="Автоматическая раскладка"
      aria-label="Автоматическая раскладка"
      @click="emit('autoLayout')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="4" y="4" width="6" height="6" rx="1" />
        <rect x="14" y="4" width="6" height="6" rx="1" />
        <rect x="9" y="14" width="6" height="6" rx="1" />
      </svg>
    </button>
  </div>
</template>
