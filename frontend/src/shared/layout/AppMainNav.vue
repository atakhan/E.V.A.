<script setup lang="ts">
import { useRoute } from "vue-router";
import { appNavItems, isAppNavActive } from "@/shared/layout/appNav";

const route = useRoute();
</script>

<template>
  <nav class="flex justify-center" aria-label="Главное меню">
    <ul class="menu menu-horizontal menu-lg max-w-full flex-wrap justify-center gap-1 px-0 sm:flex-nowrap sm:gap-2">
      <li v-for="item in appNavItems" :key="item.id">
        <RouterLink
          :to="item.to"
          class="whitespace-nowrap"
          :class="{ 'menu-active': isAppNavActive(item, route) }"
          :aria-current="isAppNavActive(item, route) ? 'page' : undefined"
        >
          {{ item.label }}
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
