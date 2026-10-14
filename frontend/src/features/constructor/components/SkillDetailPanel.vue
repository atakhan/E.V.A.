<script setup lang="ts">
import type { Skill } from "@/features/skills/types/skill";
import { formatDateTime } from "@/shared/utils/formatDate";

defineProps<{
  skill: Skill;
}>();

const emit = defineEmits<{
  close: [];
  openEditor: [];
  remove: [];
}>();
</script>

<template>
  <aside
    class="absolute inset-y-0 right-0 z-30 flex w-[22rem] flex-col border-l border-base-300/60 bg-base-100 shadow-xl sm:w-96"
    data-canvas-ui
  >
    <header class="flex items-start justify-between gap-2 border-b border-base-300 px-4 py-3">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-wide text-base-content/50">Навык</p>
        <h2 class="mt-0.5 truncate text-base font-semibold">{{ skill.name }}</h2>
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

    <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 text-sm">
      <p v-if="skill.description" class="text-base-content/70">
        {{ skill.description }}
      </p>
      <p v-else class="text-base-content/50">Без описания</p>

      <dl class="space-y-2 text-xs">
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Версия</dt>
          <dd class="font-mono">{{ skill.version }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Состояния</dt>
          <dd>{{ skill.states.length }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Initial</dt>
          <dd class="font-mono">{{ skill.initial ?? "—" }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Обновлён</dt>
          <dd>{{ formatDateTime(skill.updatedAt) }}</dd>
        </div>
      </dl>
    </div>

    <footer class="flex flex-col gap-2 border-t border-base-300 p-3">
      <button type="button" class="btn btn-sm btn-primary" @click="emit('openEditor')">
        Открыть редактор
      </button>
      <button type="button" class="btn btn-sm btn-ghost text-error" @click="emit('remove')">
        Удалить навык
      </button>
    </footer>
  </aside>
</template>
