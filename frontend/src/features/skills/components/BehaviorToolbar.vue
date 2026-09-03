<script setup lang="ts">
import type { BehaviorTool } from "@/features/skills/types/behavior";

defineProps<{
  activeTool: BehaviorTool;
}>();

const emit = defineEmits<{
  "update:activeTool": [tool: BehaviorTool];
}>();
</script>

<template>
  <div
    class="absolute bottom-5 left-1/2 z-20 flex -translate-x-1/2 items-center gap-1 rounded-2xl border border-base-300/60 bg-base-100/90 p-1.5 shadow-lg backdrop-blur-sm"
    role="toolbar"
    aria-label="Инструменты поведения"
  >
    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': activeTool === 'select' }"
      title="Выбор"
      @click="emit('update:activeTool', 'select')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 4l8 18 2.5-7.5L22 12 4 4z" />
      </svg>
    </button>
    <button
      type="button"
      class="btn btn-sm"
      :class="{ 'btn-active': activeTool === 'wait' }"
      title="Когда / жду"
      @click="emit('update:activeTool', 'wait')"
    >
      Когда
    </button>
    <button
      type="button"
      class="btn btn-sm"
      :class="{ 'btn-active': activeTool === 'do' }"
      title="Я делаю"
      @click="emit('update:activeTool', 'do')"
    >
      Я…
    </button>
    <button
      type="button"
      class="btn btn-sm"
      :class="{ 'btn-active': activeTool === 'decide' }"
      title="Если"
      @click="emit('update:activeTool', 'decide')"
    >
      Если
    </button>
    <button
      type="button"
      class="btn btn-sm"
      :class="{ 'btn-active': activeTool === 'end' }"
      title="Задача завершена"
      @click="emit('update:activeTool', 'end')"
    >
      Конец
    </button>
    <button
      type="button"
      class="btn btn-sm btn-square"
      :class="{ 'btn-active': activeTool === 'connect' }"
      title="Связать шаги"
      @click="emit('update:activeTool', 'connect')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 12h12" />
        <path d="M14 7l5 5-5 5" />
      </svg>
    </button>
  </div>
</template>
