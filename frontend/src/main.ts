import { createApp } from "vue";
import App from "@/App.vue";
import router from "@/router";
import { loadToolCatalog } from "@/features/tools/registry/builtinTools";
import "@/style.css";

async function bootstrap() {
  await loadToolCatalog();
  createApp(App).use(router).mount("#app");
}

void bootstrap();
