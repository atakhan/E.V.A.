<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  createCredential,
  verifyCredential,
  type ToolCredential,
} from "@/features/tools/services/credentialsApi";
import {
  fetchWebClientIntegration,
  generateInboundKey,
  type WebClientIntegrationInfo,
} from "@/features/tools/services/webClientApi";
import ToolLogFeed from "@/features/tools/components/ToolLogFeed.vue";
import WebClientSetupGuide from "@/features/tools/components/WebClientSetupGuide.vue";
import {
  parseWebClientConfigNote,
  serializeWebClientConfigNote,
  type WebClientBindingConfig,
} from "@/features/tools/utils/webClientConfig";
import { webClientEnvSnippet, webClientIngressUrlFallback } from "@/features/tools/utils/webClientCredentialCopy";

const props = defineProps<{
  agentSlug: string;
  credentials: ToolCredential[];
  selectedCredentialId: string;
  configNote: string;
  busy?: boolean;
  /** `app` — одно приложение (адрес). Контракт путей остаётся на канале. */
  mode?: "full" | "app";
}>();

const emit = defineEmits<{
  "update:selectedCredentialId": [value: string];
  "update:configNote": [value: string];
  refreshCredentials: [];
  error: [message: string | null];
}>();

const backendUrl = ref("");
const outboundKey = ref("");
const inboundKeyDraft = ref("");
const revealedInboundKey = ref<string | null>(null);
const integration = ref<WebClientIntegrationInfo | null>(null);
const localBusy = ref(false);
const loadingIntegration = ref(false);
const editing = ref(false);
const envCopyModalOpen = ref(false);
const envSnippet = ref("");
const successMessage = ref<string | null>(null);
const showOutboundKey = ref(false);
const showInboundKey = ref(false);

const webCredentials = computed(() =>
  props.credentials.filter((item) => item.toolId === "web_client"),
);

const selectedCredential = computed(() =>
  webCredentials.value.find((item) => item.id === props.selectedCredentialId) ?? null,
);

const bindingConfig = computed({
  get: () => parseWebClientConfigNote(props.configNote),
  set(value: WebClientBindingConfig) {
    emit("update:configNote", serializeWebClientConfigNote(value));
  },
});

const isBusy = computed(() => props.busy || localBusy.value);
const showForm = computed(() => editing.value || !props.selectedCredentialId);
const connectedUrl = computed(
  () => selectedCredential.value?.meta.backend_base_url || integration.value?.outboundBaseUrl || "",
);

function buildEnvSnippet(options?: { inboundKey?: string | null; outboundKey?: string | null }) {
  const inbound =
    options?.inboundKey ??
    revealedInboundKey.value ??
    (inboundKeyDraft.value.trim() || undefined);
  const outbound = options?.outboundKey ?? (outboundKey.value.trim() || undefined);
  return webClientEnvSnippet({
    ingressUrl:
      integration.value?.ingressUrl ?? webClientIngressUrlFallback(props.agentSlug),
    outboundKey: outbound,
    inboundKey: inbound,
  });
}

function openEnvCopyModal() {
  envSnippet.value = buildEnvSnippet();
  envCopyModalOpen.value = true;
}

function closeEnvCopyModal() {
  envCopyModalOpen.value = false;
}

const ingressCurl = computed(() => {
  if (!integration.value) return "";
  const key = revealedInboundKey.value || "<INBOUND_API_KEY>";
  return `curl -X POST '${integration.value.ingressUrl}' \\
  -H 'Authorization: Bearer ${key}' \\
  -H 'Content-Type: application/json' \\
  -d '{"sessionId":"web:demo:1","type":"channel.message.received","payload":{"text":"Привет"}}'`;
});

async function loadIntegration() {
  if (!props.selectedCredentialId) {
    integration.value = null;
    return;
  }
  loadingIntegration.value = true;
  try {
    integration.value = await fetchWebClientIntegration(
      props.agentSlug,
      props.selectedCredentialId,
    );
  } catch (error) {
    integration.value = null;
    emit("error", error instanceof Error ? error.message : "Не удалось загрузить integration info");
  } finally {
    loadingIntegration.value = false;
  }
}

watch(
  () => [props.agentSlug, props.selectedCredentialId] as const,
  () => {
    void loadIntegration();
  },
  { immediate: true },
);

function startEditing() {
  editing.value = true;
  successMessage.value = null;
  backendUrl.value = "";
  outboundKey.value = "";
  inboundKeyDraft.value = "";
}

function cancelEditing() {
  editing.value = false;
}

async function addCredential() {
  if (!backendUrl.value.trim() || !outboundKey.value.trim()) return;
  localBusy.value = true;
  emit("error", null);
  try {
    let name = "Web backend";
    try {
      name = new URL(backendUrl.value.trim()).host || name;
    } catch {
      name = backendUrl.value.trim();
    }
    const created = await createCredential(props.agentSlug, {
      toolId: "web_client",
      name,
      backendBaseUrl: backendUrl.value.trim(),
      outboundApiKey: outboundKey.value.trim(),
      inboundApiKey: inboundKeyDraft.value.trim() || undefined,
    });
    const inboundSecret =
      created.oneTimeSecrets?.inboundApiKey ??
      (inboundKeyDraft.value.trim() || undefined);
    revealedInboundKey.value = inboundSecret ?? null;
    emit("update:selectedCredentialId", created.id);
    emit("refreshCredentials");
    editing.value = false;
    await loadIntegration();
    envSnippet.value = buildEnvSnippet({
      inboundKey: inboundSecret,
      outboundKey: outboundKey.value.trim(),
    });
    envCopyModalOpen.value = true;
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Не удалось сохранить credential");
  } finally {
    localBusy.value = false;
  }
}

async function verify() {
  if (!props.selectedCredentialId) return;
  localBusy.value = true;
  emit("error", null);
  successMessage.value = null;
  try {
    const verified = await verifyCredential(props.agentSlug, props.selectedCredentialId);
    emit("refreshCredentials");
    await loadIntegration();
    const latency = verified.meta.latency_ms;
    const status = verified.meta.health_status;
    successMessage.value =
      latency != null && status != null
        ? `Связь есть: HTTP ${status}, ${latency} ms`
        : "Связь есть";
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Проверка не удалась");
    emit("refreshCredentials");
  } finally {
    localBusy.value = false;
  }
}

async function genInboundKey() {
  try {
    inboundKeyDraft.value = await generateInboundKey(props.agentSlug);
    showInboundKey.value = true;
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Не удалось сгенерировать ключ");
  }
}

function copyText(text: string) {
  void navigator.clipboard.writeText(text);
}

function updateConfigField<K extends keyof WebClientBindingConfig>(key: K, value: WebClientBindingConfig[K]) {
  bindingConfig.value = { ...bindingConfig.value, [key]: value };
}
</script>

<template>
  <div class="space-y-3">
    <p class="text-xs leading-snug text-base-content/60">
      {{
        mode === "app"
          ? "Одно приложение: его адрес и два ключа."
          : "Адрес вашего приложения и два ключа. E.V.A. стучится к вам, вы стучитесь в E.V.A."
      }}
    </p>

    <section v-if="showForm" class="space-y-2">
      <label class="form-control w-full gap-1">
        <span class="label-text text-xs">Адрес приложения</span>
        <input
          v-model="backendUrl"
          class="input input-bordered input-sm w-full font-mono text-xs"
          placeholder="http://localhost:8765"
          autocomplete="off"
        />
      </label>
      <label class="form-control w-full gap-1">
        <span class="label-text text-xs">Ключ, с которым E.V.A. стучится к вам</span>
        <input
          v-model="outboundKey"
          :type="showOutboundKey ? 'text' : 'password'"
          class="input input-bordered input-sm w-full font-mono text-xs"
          autocomplete="off"
        />
        <button
          type="button"
          class="text-left text-[11px] text-base-content/50 underline-offset-2 hover:underline"
          @click="showOutboundKey = !showOutboundKey"
        >
          {{ showOutboundKey ? "Скрыть" : "Показать" }}
        </button>
      </label>
      <label class="form-control w-full gap-1">
        <span class="label-text text-xs">Ключ, с которым вы стучитесь в E.V.A.</span>
        <input
          v-model="inboundKeyDraft"
          :type="showInboundKey ? 'text' : 'password'"
          class="input input-bordered input-sm w-full font-mono text-xs"
          placeholder="Пусто — E.V.A. сгенерирует"
          autocomplete="off"
        />
        <span class="flex gap-3 text-[11px]">
          <button
            type="button"
            class="text-base-content/50 underline-offset-2 hover:underline"
            @click="showInboundKey = !showInboundKey"
          >
            {{ showInboundKey ? "Скрыть" : "Показать" }}
          </button>
          <button
            type="button"
            class="text-base-content/50 underline-offset-2 hover:underline"
            @click="genInboundKey"
          >
            Сгенерировать
          </button>
        </span>
      </label>
      <div class="flex gap-2 pt-1">
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="isBusy || !backendUrl.trim() || !outboundKey.trim()"
          @click="addCredential"
        >
          {{ isBusy ? "Сохранение…" : "Подключить" }}
        </button>
        <button
          v-if="selectedCredentialId"
          type="button"
          class="btn btn-ghost btn-sm"
          @click="cancelEditing"
        >
          Отмена
        </button>
      </div>
    </section>

    <section v-else class="space-y-2">
      <div class="rounded-xl border border-base-300 bg-base-100 px-3 py-2">
        <p class="truncate text-sm font-medium">{{ selectedCredential?.name ?? "Приложение" }}</p>
        <p class="truncate font-mono text-[11px] text-base-content/55">
          {{ connectedUrl || "Адрес не указан" }}
        </p>
      </div>

      <label v-if="webCredentials.length > 1" class="form-control w-full gap-1">
        <span class="label-text text-xs">Подключение</span>
        <select
          class="select select-bordered select-sm w-full"
          :value="selectedCredentialId"
          @change="emit('update:selectedCredentialId', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="item in webCredentials" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
      </label>

      <div class="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="!selectedCredentialId || isBusy"
          @click="verify"
        >
          Проверить связь
        </button>
        <button type="button" class="btn btn-sm" :disabled="!integration" @click="openEnvCopyModal">
          Скопировать .env
        </button>
        <span v-if="selectedCredential?.meta.verified" class="badge badge-success badge-sm">
          связь есть
        </span>
      </div>
      <p v-if="successMessage" class="text-xs text-success">{{ successMessage }}</p>
      <button
        type="button"
        class="text-xs text-base-content/50 underline-offset-2 hover:underline"
        @click="startEditing"
      >
        Другой адрес
      </button>
    </section>

    <section
      v-if="mode !== 'app'"
      class="collapse collapse-arrow rounded-xl border border-base-300/80 bg-base-100/40"
    >
      <input type="checkbox" />
      <div class="collapse-title min-h-0 py-2.5 text-xs font-medium">Контракт, пути и журнал</div>
      <div class="collapse-content space-y-3 pb-3">
        <div class="grid grid-cols-1 gap-2">
          <label class="form-control gap-0.5">
            <span class="label-text text-[11px] text-base-content/60">Health</span>
            <input
              class="input input-bordered input-sm w-full font-mono text-xs"
              :value="bindingConfig.healthPath"
              @input="updateConfigField('healthPath', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="form-control gap-0.5">
            <span class="label-text text-[11px] text-base-content/60">Сообщения</span>
            <input
              class="input input-bordered input-sm w-full font-mono text-xs"
              :value="bindingConfig.sendMessagePath"
              @input="updateConfigField('sendMessagePath', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="form-control gap-0.5">
            <span class="label-text text-[11px] text-base-content/60">Снимок</span>
            <input
              class="input input-bordered input-sm w-full font-mono text-xs"
              :value="bindingConfig.getSnapshotPath"
              @input="updateConfigField('getSnapshotPath', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="form-control gap-0.5">
            <span class="label-text text-[11px] text-base-content/60">Как передавать ключ</span>
            <select
              class="select select-bordered select-sm w-full text-xs"
              :value="bindingConfig.authStyle"
              @change="updateConfigField('authStyle', ($event.target as HTMLSelectElement).value as 'bearer' | 'x-api-key')"
            >
              <option value="bearer">Bearer</option>
              <option value="x-api-key">X-Api-Key</option>
            </select>
          </label>
        </div>

        <div v-if="integration" class="space-y-2 text-xs">
          <div>
            <p class="text-[11px] text-base-content/50">Куда слать события</p>
            <p class="mt-0.5 break-all font-mono leading-snug">{{ integration.ingressUrl }}</p>
          </div>
          <p v-if="revealedInboundKey" class="break-all font-mono text-warning">
            {{ revealedInboundKey }}
          </p>
          <p v-else class="text-base-content/55">
            Ключ к E.V.A.: {{ integration.inboundApiKeyHint }}. Полный ключ показывается один раз при подключении.
          </p>
          <div class="flex flex-wrap gap-1.5">
            <button type="button" class="btn btn-xs" @click="copyText(integration.ingressUrl)">
              Копировать адрес
            </button>
            <button type="button" class="btn btn-xs" @click="copyText(ingressCurl)">Копировать curl</button>
          </div>
          <p class="font-mono text-[11px] leading-snug text-base-content/55">
            Из Docker E.V.A. ходит на
            {{ integration.outboundBaseUrlDocker || integration.outboundBaseUrl || "—" }}
          </p>
        </div>
        <p v-else-if="loadingIntegration" class="text-xs text-base-content/50">Загрузка…</p>

        <WebClientSetupGuide
          :agent-slug="agentSlug"
          :binding-config="bindingConfig"
          :integration="integration"
          :ingress-curl="ingressCurl"
          :has-credential="!!selectedCredentialId"
        />

        <ToolLogFeed
          :agent-slug="agentSlug"
          tool-id="web_client"
          :credential-id="selectedCredentialId || undefined"
          compact
          show-link-to-all
          :auto-refresh-ms="5000"
          empty-text="Пока нет вызовов Web Client"
        />
      </div>
    </section>

    <dialog class="modal" :class="{ 'modal-open': envCopyModalOpen }">
      <div class="modal-box max-w-lg">
        <h3 class="text-lg font-semibold">Блок для .env приложения</h3>
        <p class="mt-1 text-sm text-base-content/60">
          Вставьте в конфиг приложения. Ключ к E.V.A. больше не будет показан целиком.
        </p>
        <pre
          class="mt-4 max-h-64 overflow-auto rounded-lg border border-base-300 bg-base-200/50 p-3 font-mono text-[11px] leading-snug"
        >{{ envSnippet }}</pre>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost btn-sm" @click="closeEnvCopyModal">Закрыть</button>
          <button type="button" class="btn btn-primary btn-sm" @click="copyText(envSnippet)">
            Копировать
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="closeEnvCopyModal">
        <button type="submit">close</button>
      </form>
    </dialog>
  </div>
</template>
