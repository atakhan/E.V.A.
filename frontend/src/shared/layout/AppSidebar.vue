<script setup lang="ts">
import { useRoute } from "vue-router";
import EvaBrand from "@/shared/components/EvaBrand.vue";
import { appNavItems, isAppNavActive } from "@/shared/layout/appNav";
import { agentsPath } from "@/router/paths";

const route = useRoute();
</script>

<template>
  <div class="flex flex-col">
    <div class="border-b border-base-300 px-4 py-4">
      <RouterLink
        :to="agentsPath()"
        class="block rounded-lg transition-colors hover:bg-base-200"
      >
        <EvaBrand size="sm" :show-tagline="false" title-class="text-base" />
      </RouterLink>
    </div>

    <nav class="p-3" aria-label="Главное меню">
      <ul class="menu menu-md w-full gap-1 p-0">
        <li v-for="item in appNavItems" :key="item.id">
          <RouterLink
            :to="item.to"
            class="rounded-lg font-medium"
            :class="{ 'menu-active': isAppNavActive(item, route) }"
          >
            {{ item.label }}
          </RouterLink>
        </li>
      </ul>
    </nav>
  </div>
</template>
