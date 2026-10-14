<script setup lang="ts">
import AppFloatingChrome from "@/shared/layout/AppFloatingChrome.vue";
</script>

<template>
  <div class="h-screen min-h-0 bg-base-200">
    <AppFloatingChrome />

    <main class="h-full min-h-0 min-w-0 overflow-y-auto pt-[4.75rem]">
      <RouterView />
    </main>
  </div>
</template>
