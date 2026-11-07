import { computed, ref } from "vue";
import {
  fetchMe,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type AuthCredentials,
  type AuthUser,
} from "@/features/auth/services/authApi";
import { setUnauthorizedHandler } from "@/shared/api/http";

const user = ref<AuthUser | null>(null);
const ready = ref(false);
const loading = ref(false);

export function useAuthStore() {
  const isAuthenticated = computed(() => user.value !== null);

  async function loadMe(): Promise<AuthUser | null> {
    loading.value = true;
    try {
      user.value = await fetchMe();
      return user.value;
    } catch {
      user.value = null;
      return null;
    } finally {
      ready.value = true;
      loading.value = false;
    }
  }

  async function login(credentials: AuthCredentials): Promise<AuthUser> {
    user.value = await loginRequest(credentials);
    ready.value = true;
    return user.value;
  }

  async function register(credentials: AuthCredentials): Promise<AuthUser> {
    user.value = await registerRequest(credentials);
    ready.value = true;
    return user.value;
  }

  async function logout(): Promise<void> {
    try {
      await logoutRequest();
    } finally {
      user.value = null;
    }
  }

  function clearSession() {
    user.value = null;
  }

  return {
    user,
    ready,
    loading,
    isAuthenticated,
    loadMe,
    login,
    register,
    logout,
    clearSession,
  };
}

setUnauthorizedHandler(() => {
  user.value = null;
});
