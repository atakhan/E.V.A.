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
import { WEB_CLIENT_CREDENTIAL_COPY, webClientEnvSnippet, webClientIngressUrlFallback } from "@/features/tools/utils/webClientCredentialCopy";

const credentialCopy = WEB_CLIENT_CREDENTIAL_COPY;

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
const credentialModalOpen = ref(false);
const envCopyModalOpen = ref(false);
const envSnippet = ref("");
const showOutboundKey = ref(false);
const showInboundKey = ref(false);
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

const hasCredential = computed(() => !!props.selectedCredentialId);
const isVerified = computed(() => !!selectedCredential.value?.meta.verified);

const wizardStep = computed(() => {
  if (!hasCredential.value) return 1;
  if (!isVerified.value) return 2;
  return 3;
});

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

function openCredentialModal() {
  credentialModalOpen.value = true;
}

function closeCredentialModal() {
  credentialModalOpen.value = false;
  showOutboundKey.value = false;
  showInboundKey.value = false;
}

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
    const inboundSecret =
      created.oneTimeSecrets?.inboundApiKey ??
      (inboundKeyDraft.value.trim() || undefined);
    revealedInboundKey.value = inboundSecret ?? null;
    emit("update:selectedCredentialId", created.id);
    emit("refreshCredentials");
    closeCredentialModal();
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
  <div class="mt-6 space-y-4">
    <WebClientSetupGuide
      :agent-slug="agentSlug"
      :binding-config="bindingConfig"
      :integration="integration"
      :ingress-curl="ingressCurl"
      :has-credential="!!selectedCredentialId"
    />

    <div class="space-y-3 rounded-xl border border-base-300 bg-base-200/20 p-4">
    <div>
      <h4 class="text-sm font-semibold">Подключение</h4>
      <p class="mt-0.5 text-xs leading-snug text-base-content/60">
        Три шага: credential → verify → скопировать секреты в .env бэкенда
      </p>
    </div>

    <ul class="steps steps-horizontal w-full text-[11px]">
      <li class="step" :class="wizardStep >= 1 ? 'step-primary' : ''">1. Credential</li>
      <li class="step" :class="wizardStep >= 2 ? 'step-primary' : ''">2. Verify</li>
      <li class="step" :class="wizardStep >= 3 ? 'step-primary' : ''">3. .env</li>
    </ul>

    <!-- Credential -->
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
        <button
          type="button"
          class="btn btn-sm"
          :class="wizardStep === 2 ? 'btn-primary' : ''"
          :disabled="!selectedCredentialId || isBusy"
          @click="verify"
        >
          Verify
        </button>
        <button
          v-if="wizardStep >= 3"
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="!integration"
          @click="openEnvCopyModal"
        >
          Скопировать .env
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
          @click="openCredentialModal"
        >
          + Credential
        </button>
      </div>
      <p v-if="successMessage" class="text-xs text-success">{{ successMessage }}</p>
      <p v-if="!selectedCredentialId" class="text-xs text-warning">
        Создайте или выберите credential (шаг 1).
      </p>
      <p v-else-if="!isVerified" class="text-xs text-warning">
        Нажмите Verify — E.V.A. проверит доступ к вашему бэкенду (шаг 2).
      </p>
      <p v-else class="text-xs text-base-content/55">
        Скопируйте блок .env в конфиг приложения (шаг 3).
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
          <p class="text-[11px] uppercase tracking-wide text-base-content/50">
            {{ credentialCopy.inbound.fieldLabel }}
          </p>
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

    <dialog class="modal" :class="{ 'modal-open': credentialModalOpen }">
      <div class="modal-box max-w-lg">
        <h3 class="text-lg font-semibold">Новый credential</h3>
        <p class="mt-1 text-sm text-base-content/60">
          Секреты задаются здесь в E.V.A.; те же значения — в <code class="font-mono text-xs">.env</code>
          вашего бэкенда (см. таблицу).
        </p>

        <div class="mt-3 overflow-x-auto rounded-lg border border-base-300 bg-base-200/40">
          <table class="table table-xs">
            <thead>
              <tr>
                <th>Направление</th>
                <th>Здесь в E.V.A.</th>
                <th>В .env бэкенда</th>
              </tr>
            </thead>
            <tbody class="text-[11px]">
              <tr>
                <td>{{ credentialCopy.outbound.direction }}</td>
                <td class="font-medium">{{ credentialCopy.outbound.fieldLabel }}</td>
                <td class="font-mono">{{ credentialCopy.outbound.backendEnvVar }}</td>
              </tr>
              <tr>
                <td>{{ credentialCopy.inbound.direction }}</td>
                <td class="font-medium">{{ credentialCopy.inbound.fieldLabel }}</td>
                <td class="font-mono">{{ credentialCopy.inbound.backendEnvVar }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label class="form-control gap-1 sm:col-span-2">
            <span class="label-text text-xs">Название</span>
            <input v-model="credentialName" class="input input-bordered input-sm w-full" />
          </label>
          <label class="form-control gap-1 sm:col-span-2">
            <span class="label-text text-xs">Backend base URL</span>
            <input
              v-model="backendUrl"
              class="input input-bordered input-sm w-full font-mono text-xs"
              placeholder="http://localhost:8765"
            />
          </label>
          <label class="form-control gap-1">
            <span class="label-text text-xs font-medium">{{ credentialCopy.outbound.fieldLabel }}</span>
            <span class="text-[11px] leading-snug text-base-content/55">
              → <code class="font-mono">{{ credentialCopy.outbound.backendEnvVar }}</code> ·
              {{ credentialCopy.outbound.fieldHint }}
            </span>
            <div class="join w-full">
              <input
                v-model="outboundKey"
                :type="showOutboundKey ? 'text' : 'password'"
                class="input input-bordered input-sm join-item w-full min-w-0 font-mono text-xs"
                autocomplete="off"
              />
              <button
                type="button"
                class="btn btn-sm btn-square join-item"
                :title="showOutboundKey ? 'Скрыть ключ' : 'Показать ключ'"
                :aria-label="showOutboundKey ? 'Скрыть ключ' : 'Показать ключ'"
                @click="showOutboundKey = !showOutboundKey"
              >
                <svg
                  v-if="showOutboundKey"
                  viewBox="0 0 24 24"
                  class="size-4"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
                  />
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  class="size-4"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              </button>
            </div>
          </label>
          <label class="form-control gap-1">
            <span class="label-text text-xs font-medium">{{ credentialCopy.inbound.fieldLabel }}</span>
            <span class="text-[11px] leading-snug text-base-content/55">
              → <code class="font-mono">{{ credentialCopy.inbound.backendEnvVar }}</code> ·
              {{ credentialCopy.inbound.fieldHint }}
            </span>
            <div class="join w-full">
              <input
                v-model="inboundKeyDraft"
                :type="showInboundKey ? 'text' : 'password'"
                class="input input-bordered input-sm join-item w-full min-w-0 font-mono text-xs"
                placeholder="авто"
                autocomplete="off"
              />
              <button
                type="button"
                class="btn btn-sm btn-square join-item"
                :title="showInboundKey ? 'Скрыть ключ' : 'Показать ключ'"
                :aria-label="showInboundKey ? 'Скрыть ключ' : 'Показать ключ'"
                @click="showInboundKey = !showInboundKey"
              >
                <svg
                  v-if="showInboundKey"
                  viewBox="0 0 24 24"
                  class="size-4"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
                  />
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  class="size-4"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              </button>
              <button type="button" class="btn btn-sm join-item" @click="genInboundKey">Gen</button>
            </div>
          </label>
        </div>

        <p class="mt-3 text-[11px] leading-snug text-base-content/50">
          ai_supplier в Docker:
          <code class="font-mono">http://host.docker.internal:3000</code>
          · stub:
          <code class="font-mono">web-client-stub:8765</code>
        </p>

        <div class="modal-action">
          <button type="button" class="btn btn-ghost btn-sm" @click="closeCredentialModal">
            Отмена
          </button>
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="isBusy || !backendUrl.trim() || !outboundKey.trim()"
            @click="addCredential"
          >
            {{ isBusy ? "Сохранение…" : "Сохранить" }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="closeCredentialModal">
        <button type="submit">close</button>
      </form>
    </dialog>

    <dialog class="modal" :class="{ 'modal-open': envCopyModalOpen }">
      <div class="modal-box max-w-lg">
        <h3 class="text-lg font-semibold">Секреты для .env бэкенда</h3>
        <p class="mt-1 text-sm text-base-content/60">
          Вставьте в <code class="font-mono text-xs">.env</code> вашего приложения. Значения совпадают
          с credential в E.V.A.
        </p>
        <pre
          class="mt-4 max-h-64 overflow-auto rounded-lg border border-base-300 bg-base-200/50 p-3 font-mono text-[11px] leading-snug"
        >{{ envSnippet }}</pre>
        <p class="mt-2 text-xs text-warning">
          Inbound key показывается один раз — сохраните его сейчас.
        </p>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost btn-sm" @click="closeEnvCopyModal">
            Закрыть
          </button>
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
