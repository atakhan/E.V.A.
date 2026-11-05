<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { RouteNames } from "@/router/paths";

const route = useRoute();
const fullBleed = computed(() => route.name === RouteNames.projectDesk);
</script>

<template>
  <div class="h-screen min-h-0 bg-base-200">
    <main
      class="h-full min-h-0 min-w-0"
      :class="fullBleed ? 'overflow-hidden' : 'overflow-y-auto pt-[4.75rem]'"
    >
      <RouterView />
    </main>
  </div>
</template>
