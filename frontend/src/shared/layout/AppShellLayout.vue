<script setup lang="ts">
import AppSidebar from "@/shared/layout/AppSidebar.vue";
</script>

<template>
  <div class="flex h-screen min-h-0 bg-base-200">
    <aside class="flex w-64 shrink-0 flex-col border-r border-base-300 bg-base-100">
      <AppSidebar />
    </aside>

    <main class="min-h-0 min-w-0 flex-1 overflow-y-auto">
      <RouterView />
    </main>
  </div>
</template>
