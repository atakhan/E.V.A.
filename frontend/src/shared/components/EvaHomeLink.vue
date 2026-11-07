<script setup lang="ts">
import { projectsPath } from "@/router/paths";
</script>

<template>
  <RouterLink
    :to="projectsPath()"
    class="fixed left-4 top-4 z-40 flex size-11 items-center justify-center rounded-box border border-base-300/60 bg-base-100/90 shadow-lg backdrop-blur-sm transition-colors hover:bg-base-200"
    aria-label="E.V.A., к проектам"
    title="E.V.A."
  >
    <img src="/eva-logo.png" alt="" width="32" height="32" class="size-8 rounded-lg" />
  </RouterLink>
</template>
