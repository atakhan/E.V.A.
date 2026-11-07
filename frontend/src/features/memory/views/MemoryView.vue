<script setup lang="ts">
import { toRef } from "vue";
import MemoryReadout from "@/features/memory/components/MemoryReadout.vue";
import { useAgentMemory } from "@/features/memory/composables/useAgentMemory";

const props = defineProps<{
  agentSlug: string;
}>();

const { memory, loading, error } = useAgentMemory(toRef(props, "agentSlug"));
</script>

<template>
  <section class="mx-auto max-w-3xl space-y-6">
    <div>
      <h2 class="text-lg font-semibold">Память</h2>
      <p class="mt-1 text-sm text-base-content/60">
        История событий агента и рабочее состояние его прогонов: текущее состояние, params и vars.
      </p>
    </div>
    <MemoryReadout :agent-slug="agentSlug" :memory="memory" :loading="loading" :error="error" />
  </section>
</template>
