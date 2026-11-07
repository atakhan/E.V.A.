<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/features/auth/stores/authStore";
import { loginPath, RouteNames } from "@/router/paths";

const route = useRoute();
const router = useRouter();
const { user, logout } = useAuthStore();
const fullBleed = computed(() => route.name === RouteNames.projects);

async function onLogout() {
  await logout();
  await router.replace(loginPath());
}
</script>

<template>
  <div class="h-screen min-h-0 bg-base-200">
    <header
      v-if="user"
      class="absolute right-4 top-3 z-40 flex items-center gap-3 rounded-box border border-base-300/60 bg-base-100/90 px-3 py-1.5 text-sm shadow-sm backdrop-blur-sm"
    >
      <span class="max-w-[14rem] truncate text-base-content/70">{{ user.email }}</span>
      <button type="button" class="btn btn-ghost btn-xs" @click="onLogout">Выйти</button>
    </header>
    <main
      class="h-full min-h-0 min-w-0"
      :class="fullBleed ? 'overflow-hidden' : 'overflow-y-auto pt-[4.75rem]'"
    >
      <RouterView />
    </main>
  </div>
</template>
