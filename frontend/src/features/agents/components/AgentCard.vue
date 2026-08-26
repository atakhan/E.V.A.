<script setup lang="ts">
import { formatDateTime } from "@/shared/utils/formatDate";
import type { Agent } from "@/features/agents/types/agent";

defineProps<{
  agent: Agent;
}>();

const emit = defineEmits<{
  open: [];
  edit: [];
  remove: [];
}>();
</script>

<template>
  <article class="card border border-base-300 bg-base-100 shadow-sm transition hover:shadow-md">
    <div class="card-body gap-3">
      <button type="button" class="text-left" @click="emit('open')">
        <h2 class="text-lg font-semibold hover:text-primary">{{ agent.name }}</h2>
        <p class="mt-1 font-mono text-xs text-base-content/50">/{{ agent.slug }}</p>
        <p
          v-if="agent.description"
          class="mt-2 line-clamp-2 text-sm text-base-content/60"
        >
          {{ agent.description }}
        </p>
        <p v-else class="mt-2 text-sm text-base-content/40">Без описания</p>
      </button>

      <p class="text-xs text-base-content/50">
        Обновлено {{ formatDateTime(agent.updatedAt) }}
      </p>

      <div class="card-actions justify-end">
        <button type="button" class="btn btn-xs btn-ghost" @click="emit('edit')">
          Редактировать
        </button>
        <button type="button" class="btn btn-xs btn-ghost text-error" @click="emit('remove')">
          Удалить
        </button>
      </div>
    </div>
  </article>
</template>
