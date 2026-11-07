import { createApp } from "vue";
import App from "@/App.vue";
import router from "@/router";
import { useAuthStore } from "@/features/auth/stores/authStore";
import { loadToolCatalog } from "@/features/tools/registry/builtinTools";
import "@/style.css";

async function bootstrap() {
  const { loadMe, isAuthenticated } = useAuthStore();
  await loadMe();
  if (isAuthenticated.value) {
    await loadToolCatalog();
  }
  createApp(App).use(router).mount("#app");
}

void bootstrap();
