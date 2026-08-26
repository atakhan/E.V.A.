<script setup lang="ts">
import type { ModuleSection } from "@/features/workspace/config/modules";

defineProps<{
  section: ModuleSection;
}>();
</script>

<template>
  <section class="rounded-2xl border border-base-300 bg-base-100 p-6 shadow-sm">
    <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
      Раздел
    </p>
    <h2 class="mt-1 text-2xl font-semibold">{{ section.title }}</h2>
    <p class="mt-4 max-w-3xl text-base text-base-content/70">
      {{ section.description }}
    </p>
    <div
      class="mt-8 rounded-xl border border-dashed border-base-300 bg-base-200/40 px-6 py-10 text-center text-sm text-base-content/50"
    >
      Конфигурация модуля появится здесь
    </div>
  </section>
</template>
