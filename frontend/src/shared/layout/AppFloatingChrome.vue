<script setup lang="ts">
import { useRoute } from "vue-router";
import { appNavItems, isAppNavActive } from "@/shared/layout/appNav";
import { agentsPath } from "@/router/paths";

const route = useRoute();
</script>

<template>
  <div class="pointer-events-none fixed left-4 top-4 z-40 flex items-center gap-2">
    <RouterLink
      :to="agentsPath()"
      class="pointer-events-auto flex size-11 items-center justify-center rounded-box border border-base-300/60 bg-base-100/90 shadow-lg backdrop-blur-sm transition-colors hover:bg-base-200"
      aria-label="E.V.A., к агентам"
      title="E.V.A."
    >
      <img src="/eva-logo.png" alt="" width="32" height="32" class="size-8 rounded-lg" />
    </RouterLink>

    <nav
      class="pointer-events-auto flex items-center gap-0.5 rounded-box border border-base-300/60 bg-base-100/90 p-1.5 shadow-lg backdrop-blur-sm"
      aria-label="Главное меню"
    >
      <RouterLink
        v-for="item in appNavItems"
        :key="item.id"
        :to="item.to"
        class="btn btn-sm btn-square btn-ghost tooltip tooltip-bottom"
        :class="{ 'btn-active': isAppNavActive(item, route) }"
        :data-tip="item.label"
        :aria-label="item.label"
        :aria-current="isAppNavActive(item, route) ? 'page' : undefined"
      >
        <svg
          viewBox="0 0 24 24"
          class="size-4"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <template v-if="item.id === 'agents'">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </template>
          <template v-else-if="item.id === 'runtime'">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </template>
          <template v-else>
            <rect width="7" height="7" x="3" y="3" rx="1" />
            <rect width="7" height="7" x="14" y="3" rx="1" />
            <rect width="7" height="7" x="3" y="14" rx="1" />
            <rect width="7" height="7" x="14" y="14" rx="1" />
          </template>
        </svg>
      </RouterLink>
    </nav>

    <slot />
  </div>
</template>
