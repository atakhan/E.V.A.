<script setup lang="ts">
import { onMounted, onUnmounted, ref, useTemplateRef } from "vue";

defineProps<{
  title?: string;
}>();

const emit = defineEmits<{
  home: [];
  exportYaml: [];
  importYaml: [];
}>();

const helpOpen = ref(false);
const rootEl = useTemplateRef<HTMLElement>("root");

const shortcuts = [
  { keys: "Колёсико", action: "Масштаб холста" },
  { keys: "Перетаскивание фона", action: "Панорама" },
  { keys: "State", action: "Нарисовать состояние FSM" },
  { keys: "Transition", action: "Клик источник → клик цель" },
  { keys: "Delete / Backspace", action: "Удалить state или transition" },
];

function onDocumentPointerDown(event: PointerEvent) {
  if (!helpOpen.value) return;
  const target = event.target;
  if (target instanceof Node && rootEl.value?.contains(target)) return;
  helpOpen.value = false;
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
});
</script>

<template>
  <div
    ref="root"
    class="absolute left-4 top-4 z-20 flex items-center gap-1 rounded-box border border-base-300/60 bg-base-100/90 px-2 py-2 shadow-lg backdrop-blur-sm"
  >
    <button
      type="button"
      class="btn btn-xs btn-square btn-ghost"
      title="К списку Skills"
      aria-label="К списку Skills"
      @click="emit('home')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5z" />
      </svg>
    </button>

    <span class="text-sm font-semibold tracking-wide" title="Engine for Versatile Agents">E.V.A.</span>
    <span v-if="title" class="max-w-40 truncate text-xs text-base-content/60">
      / {{ title }}
    </span>

    <button
      type="button"
      class="btn btn-xs btn-ghost"
      title="Export YAML"
      @click="emit('exportYaml')"
    >
      YAML↓
    </button>
    <button
      type="button"
      class="btn btn-xs btn-ghost"
      title="Import YAML"
      @click="emit('importYaml')"
    >
      YAML↑
    </button>

    <div class="relative">
      <button
        type="button"
        class="btn btn-xs btn-circle btn-ghost"
        title="Справка"
        aria-label="Справка"
        :aria-expanded="helpOpen"
        @click="helpOpen = !helpOpen"
      >
        ?
      </button>

      <div
        v-if="helpOpen"
        class="absolute left-0 top-full mt-2 w-72 rounded-box border border-base-300 bg-base-100 p-4 shadow-xl"
      >
        <p class="mb-3 text-sm font-medium">Управление</p>
        <ul class="space-y-2">
          <li
            v-for="item in shortcuts"
            :key="item.keys"
            class="flex flex-col gap-0.5 text-sm"
          >
            <span class="font-medium">{{ item.keys }}</span>
            <span class="text-base-content/60">{{ item.action }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
