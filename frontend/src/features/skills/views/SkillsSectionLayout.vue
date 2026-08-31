<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { RouteNames } from "@/router/paths";

const route = useRoute();

const isCanvas = computed(() => route.name === RouteNames.skillCanvas);
</script>

<template>
  <div
    class="min-h-0"
    :class="isCanvas ? 'flex min-h-0 flex-1 flex-col' : ''"
  >
    <RouterView />
  </div>
</template>
