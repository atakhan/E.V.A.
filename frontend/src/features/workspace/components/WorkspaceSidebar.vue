<script setup lang="ts">
import type { ModuleSection } from "@/features/workspace/config/modules";

defineProps<{
  sections: ModuleSection[];
  activeId: string;
}>();

const emit = defineEmits<{
  select: [id: string];
}>();
</script>

<template>
  <nav class="flex flex-col gap-1 p-3" aria-label="Разделы E.V.A.">
    <template v-for="section in sections" :key="section.id">
      <button
        v-if="!section.children"
        type="button"
        class="btn btn-sm justify-start font-normal"
        :class="{ 'btn-active': activeId === section.id }"
        @click="emit('select', section.id)"
      >
        {{ section.title }}
      </button>

      <div v-else class="space-y-1">
        <p class="px-2 pt-2 text-xs font-semibold uppercase tracking-wide text-base-content/50">
          {{ section.title }}
        </p>
        <button
          v-for="child in section.children"
          :key="child.id"
          type="button"
          class="btn btn-sm w-full justify-start pl-5 font-normal"
          :class="{ 'btn-active': activeId === child.id }"
          @click="emit('select', child.id)"
        >
          {{ child.title }}
        </button>
      </div>
    </template>
  </nav>
</template>
