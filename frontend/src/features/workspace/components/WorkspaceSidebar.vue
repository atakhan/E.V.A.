<script setup lang="ts">
import type { WorkspaceSection } from "@/features/workspace/config/nav";

defineProps<{
  sections: WorkspaceSection[];
  activeId: string;
}>();

const emit = defineEmits<{
  select: [id: string];
}>();
</script>

<template>
  <nav class="flex flex-col gap-1 p-3" aria-label="Разделы агента">
    <button
      v-for="section in sections"
      :key="section.id"
      type="button"
      class="btn btn-sm justify-start font-normal"
      :class="{ 'btn-active': activeId === section.id }"
      @click="emit('select', section.id)"
    >
      {{ section.title }}
    </button>
  </nav>
</template>
