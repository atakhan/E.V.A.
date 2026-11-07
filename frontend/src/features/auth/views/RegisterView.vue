<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/features/auth/stores/authStore";
import { RouteNames } from "@/router/paths";

const email = ref("");
const password = ref("");
const error = ref("");
const submitting = ref(false);
const { register } = useAuthStore();
const router = useRouter();

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    await register({ email: email.value, password: password.value });
    await router.replace("/projects");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Не удалось зарегистрироваться";
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
      <h1 class="text-xl font-semibold text-base-content">Регистрация</h1>
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
        <span class="label-text mb-1">Пароль (от 8 символов)</span>
        <input
          v-model="password"
          type="password"
          required
          minlength="8"
          autocomplete="new-password"
          class="input input-bordered w-full"
        />
      </label>
      <p v-if="error" class="text-sm text-error">{{ error }}</p>
      <button class="btn btn-primary w-full" type="submit" :disabled="submitting">
        {{ submitting ? "Создаём…" : "Создать аккаунт" }}
      </button>
      <p class="text-center text-sm text-base-content/60">
        Уже есть аккаунт?
        <RouterLink :to="{ name: RouteNames.login }" class="link link-primary">Войти</RouterLink>
      </p>
    </form>
  </div>
</template>
