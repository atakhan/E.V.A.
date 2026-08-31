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
import {
  parseWebClientConfigNote,
  serializeWebClientConfigNote,
  type WebClientBindingConfig,
} from "@/features/tools/utils/webClientConfig";

const props = defineProps<{
  agentSlug: string;
  credentials: ToolCredential[];
  selectedCredentialId: string;
  configNote: string;
  busy?: boolean;
}>();

const emit = defineEmits<{
  "update:selectedCredentialId": [value: string];
  "update:configNote": [value: string];
  bind: [];
  refreshCredentials: [];
  error: [message: string | null];
}>();

const backendUrl = ref("http://host.docker.internal:3000");
const outboundKey = ref("dev-outbound-key");
const inboundKeyDraft = ref("");
const credentialName = ref("Local web backend");
const revealedInboundKey = ref<string | null>(null);
const integration = ref<WebClientIntegrationInfo | null>(null);
const localBusy = ref(false);
const loadingIntegration = ref(false);
const showNewCredential = ref(false);
const successMessage = ref<string | null>(null);

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

async function addCredential() {
  if (!backendUrl.value.trim() || !outboundKey.value.trim()) return;
  localBusy.value = true;
  emit("error", null);
  try {
    const created = await createCredential(props.agentSlug, {
      toolId: "web_client",
      name: credentialName.value.trim() || "Web backend",
      backendBaseUrl: backendUrl.value.trim(),
      outboundApiKey: outboundKey.value.trim(),
      inboundApiKey: inboundKeyDraft.value.trim() || undefined,
    });
    revealedInboundKey.value = created.oneTimeSecrets?.inboundApiKey ?? null;
    emit("update:selectedCredentialId", created.id);
    emit("refreshCredentials");
    emit("bind");
    showNewCredential.value = false;
    await loadIntegration();
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
        ? `Подключение успешно: HTTP ${status}, ${latency} ms`
        : "Подключение успешно";
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Verify failed");
  } finally {
    localBusy.value = false;
  }
}

async function genInboundKey() {
  try {
    inboundKeyDraft.value = await generateInboundKey(props.agentSlug);
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
  <div class="mt-6 space-y-3 rounded-xl border border-base-300 bg-base-200/20 p-4">
    <div>
      <h4 class="text-sm font-semibold">Web Client — бэкенд приложения</h4>
      <p class="mt-0.5 text-xs leading-snug text-base-content/60">
        Исходящие: E.V.A. → ваш API. Входящие: ваш API → ingress E.V.A.
      </p>
    </div>

    <!-- Подключение -->
    <section class="space-y-2">
      <label class="form-control w-full gap-1">
        <span class="label-text text-xs">Credential</span>
        <select
          class="select select-bordered select-sm w-full"
          :value="selectedCredentialId"
          @change="emit('update:selectedCredentialId', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">— не выбран —</option>
          <option v-for="item in webCredentials" :key="item.id" :value="item.id">
            {{ item.name }}
            <template v-if="item.meta.backend_base_url"> · {{ item.meta.backend_base_url }}</template>
          </option>
        </select>
      </label>

      <div class="flex flex-wrap items-center gap-1.5">
        <button type="button" class="btn btn-primary btn-sm" @click="emit('bind')">Привязать</button>
        <button type="button" class="btn btn-sm" :disabled="!selectedCredentialId || isBusy" @click="verify">
          Verify
        </button>
        <span
          v-if="selectedCredential?.meta.verified"
          class="badge badge-success badge-sm"
        >
          verified
        </span>
        <span
          v-else-if="selectedCredentialId"
          class="badge badge-ghost badge-sm"
        >
          не проверен
        </span>
        <button
          type="button"
          class="btn btn-ghost btn-sm ml-auto"
          @click="showNewCredential = !showNewCredential"
        >
          {{ showNewCredential ? "Скрыть форму" : "+ Credential" }}
        </button>
      </div>
      <p v-if="successMessage" class="text-xs text-success">{{ successMessage }}</p>
      <p v-if="!selectedCredentialId" class="text-xs text-warning">
        Выберите credential и нажмите «Привязать» перед Verify.
      </p>
    </section>

    <!-- API paths -->
    <section class="rounded-lg border border-base-300/80 bg-base-100/50 p-3">
      <p class="mb-2 text-xs font-medium text-base-content/70">Пути API</p>
      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <label class="form-control gap-0.5">
          <span class="label-text text-[11px] text-base-content/60">Health</span>
          <input
            class="input input-bordered input-sm w-full font-mono text-xs"
            :value="bindingConfig.healthPath"
            @input="updateConfigField('healthPath', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label class="form-control gap-0.5">
          <span class="label-text text-[11px] text-base-content/60">Send message</span>
          <input
            class="input input-bordered input-sm w-full font-mono text-xs"
            :value="bindingConfig.sendMessagePath"
            @input="updateConfigField('sendMessagePath', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label class="form-control gap-0.5">
          <span class="label-text text-[11px] text-base-content/60">Context / snapshot</span>
          <input
            class="input input-bordered input-sm w-full font-mono text-xs"
            :value="bindingConfig.getSnapshotPath"
            @input="updateConfigField('getSnapshotPath', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label class="form-control gap-0.5">
          <span class="label-text text-[11px] text-base-content/60">Auth style</span>
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
    </section>

    <!-- Integration -->
    <section v-if="integration" class="collapse collapse-arrow rounded-lg border border-base-300/80 bg-base-100/50">
      <input type="checkbox" checked />
      <div class="collapse-title min-h-0 py-2.5 text-xs font-medium">Ingress и локальная разработка</div>
      <div class="collapse-content space-y-2 pb-3 text-xs">
        <div>
          <p class="text-[11px] uppercase tracking-wide text-base-content/50">Ingress URL</p>
          <p class="mt-0.5 break-all font-mono leading-snug">{{ integration.ingressUrl }}</p>
        </div>
        <div>
          <p class="text-[11px] uppercase tracking-wide text-base-content/50">Inbound key</p>
          <p v-if="revealedInboundKey" class="mt-0.5 break-all font-mono text-warning">
            {{ revealedInboundKey }}
          </p>
          <p v-else class="mt-0.5 text-base-content/55">
            {{ integration.inboundApiKeyHint }} — показывается один раз при создании
          </p>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <button type="button" class="btn btn-xs" @click="copyText(integration.ingressUrl)">Copy URL</button>
          <button type="button" class="btn btn-xs" @click="copyText(ingressCurl)">Copy curl</button>
        </div>
        <dl class="grid gap-1 font-mono text-[11px] text-base-content/65">
          <div class="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5">
            <dt class="text-base-content/45">Host</dt>
            <dd class="break-all">{{ integration.localDevHints.ingressFromHost }}</dd>
            <dt class="text-base-content/45">Stub compose</dt>
            <dd class="break-all">{{ integration.localDevHints.stubInCompose }}</dd>
            <dt class="text-base-content/45">Stub host</dt>
            <dd class="break-all">{{ integration.localDevHints.stubOnHost }}</dd>
            <dt class="text-base-content/45">E.V.A.→API</dt>
            <dd class="break-all">
              {{ integration.outboundBaseUrlDocker || integration.outboundBaseUrl }}
            </dd>
          </div>
        </dl>
      </div>
    </section>
    <p v-else-if="loadingIntegration" class="text-xs text-base-content/50">Загрузка integration…</p>

    <!-- Новый credential -->
    <section
      v-show="showNewCredential"
      class="rounded-lg border border-dashed border-base-300 bg-base-100/30 p-3"
    >
      <p class="mb-2 text-xs font-medium">Новый credential</p>
      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <label class="form-control gap-0.5 sm:col-span-2">
          <span class="label-text text-xs">Название</span>
          <input v-model="credentialName" class="input input-bordered input-sm w-full" />
        </label>
        <label class="form-control gap-0.5 sm:col-span-2">
          <span class="label-text text-xs">Backend base URL</span>
          <input
            v-model="backendUrl"
            class="input input-bordered input-sm w-full font-mono text-xs"
            placeholder="http://localhost:8765"
          />
        </label>
        <label class="form-control gap-0.5">
          <span class="label-text text-xs">Outbound key</span>
          <input
            v-model="outboundKey"
            type="password"
            class="input input-bordered input-sm w-full font-mono text-xs"
            autocomplete="off"
          />
        </label>
        <label class="form-control gap-0.5">
          <span class="label-text text-xs">Inbound key</span>
          <div class="join w-full">
            <input
              v-model="inboundKeyDraft"
              type="password"
              class="input input-bordered input-sm join-item w-full min-w-0 font-mono text-xs"
              placeholder="авто"
              autocomplete="off"
            />
            <button type="button" class="btn btn-sm join-item" @click="genInboundKey">Gen</button>
          </div>
        </label>
      </div>
      <p class="mt-2 text-[11px] leading-snug text-base-content/50">
        ai_supplier в Docker:
        <code class="font-mono">http://host.docker.internal:3000</code>
        · stub:
        <code class="font-mono">web-client-stub:8765</code>
      </p>
      <div class="mt-2 flex justify-end">
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="isBusy || !backendUrl.trim() || !outboundKey.trim()"
          @click="addCredential"
        >
          Сохранить
        </button>
      </div>
    </section>

    <ToolLogFeed
      :agent-slug="agentSlug"
      tool-id="web_client"
      :credential-id="selectedCredentialId || undefined"
      compact
      show-link-to-all
      :auto-refresh-ms="5000"
      auto-refresh-default
      empty-text="Пока нет вызовов Web Client"
    />
  </div>
</template>
