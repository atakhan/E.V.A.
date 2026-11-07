<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/features/auth/stores/authStore";
import { RouteNames } from "@/router/paths";

const email = ref("");
const password = ref("");
const error = ref("");
const submitting = ref(false);
const { login } = useAuthStore();
const router = useRouter();
const route = useRoute();

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    await login({ email: email.value, password: password.value });
    const next = typeof route.query.next === "string" ? route.query.next : "/projects";
    await router.replace(next || "/projects");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Не удалось войти";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-base-200 px-4">
    <form
      class="w-full max-w-sm space-y-4 rounded-2xl border border-base-300 bg-base-100 p-6 shadow-md"
      @submit.prevent="onSubmit"
    >
      <h1 class="text-xl font-semibold text-base-content">Вход в E.V.A.</h1>
      <label class="form-control w-full">
        <span class="label-text mb-1">Email</span>
        <input
          v-model="email"
          type="email"
          required
          autocomplete="username"
          class="input input-bordered w-full"
        />
      </label>
      <label class="form-control w-full">
        <span class="label-text mb-1">Пароль</span>
        <input
          v-model="password"
          type="password"
          required
          autocomplete="current-password"
          class="input input-bordered w-full"
        />
      </label>
      <p v-if="error" class="text-sm text-error">{{ error }}</p>
      <button class="btn btn-primary w-full" type="submit" :disabled="submitting">
        {{ submitting ? "Входим…" : "Войти" }}
      </button>
      <p class="text-center text-sm text-base-content/60">
        Нет аккаунта?
        <RouterLink :to="{ name: RouteNames.register }" class="link link-primary">
          Регистрация
        </RouterLink>
      </p>
    </form>
  </div>
</template>
