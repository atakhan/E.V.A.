<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  createCredential,
  fetchPolzaBalance,
  fetchPolzaModels,
  verifyCredential,
  type PolzaModel,
  type ToolCredential,
} from "@/features/tools/services/credentialsApi";
import ToolLogFeed from "@/features/tools/components/ToolLogFeed.vue";
import {
  parsePolzaConfigNote,
  serializePolzaConfigNote,
} from "@/features/tools/utils/polzaConfig";

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

const apiKeyInput = ref("");
const credentialName = ref("Polza.ai");
const modelFilter = ref("");
const models = ref<PolzaModel[]>([]);
const balance = ref<string | null>(null);
const loadingModels = ref(false);
const loadingBalance = ref(false);
const localBusy = ref(false);

const polzaCredentials = computed(() =>
  props.credentials.filter((item) => item.toolId === "polza_ai_llm"),
);

const selectedModel = computed({
  get() {
    return parsePolzaConfigNote(props.configNote).model ?? "";
  },
  set(value: string) {
    const current = parsePolzaConfigNote(props.configNote);
    emit("update:configNote", serializePolzaConfigNote({ ...current, model: value }));
  },
});

const filteredModels = computed(() => {
  const q = modelFilter.value.trim().toLowerCase();
  if (!q) return models.value.slice(0, 80);
  return models.value
    .filter(
      (model) =>
        model.id.toLowerCase().includes(q) || model.name.toLowerCase().includes(q),
    )
    .slice(0, 80);
});

const isBusy = computed(() => props.busy || localBusy.value);

async function loadModels() {
  loadingModels.value = true;
  try {
    models.value = await fetchPolzaModels(
      props.agentSlug,
      props.selectedCredentialId || undefined,
    );
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Не удалось загрузить модели");
  } finally {
    loadingModels.value = false;
  }
}

async function loadBalance() {
  if (!props.selectedCredentialId) {
    balance.value = null;
    return;
  }
  loadingBalance.value = true;
  try {
    const result = await fetchPolzaBalance(props.agentSlug, props.selectedCredentialId);
    balance.value = result.amount;
  } catch (error) {
    balance.value = null;
    emit("error", error instanceof Error ? error.message : "Не удалось получить баланс");
  } finally {
    loadingBalance.value = false;
  }
}

watch(
  () => [props.agentSlug, props.selectedCredentialId] as const,
  () => {
    void loadModels();
    void loadBalance();
  },
  { immediate: true },
);

async function addCredential() {
  if (!apiKeyInput.value.trim()) return;
  localBusy.value = true;
  emit("error", null);
  try {
    const created = await createCredential(props.agentSlug, {
      toolId: "polza_ai_llm",
      name: credentialName.value.trim() || "Polza.ai",
      apiKey: apiKeyInput.value.trim(),
    });
    apiKeyInput.value = "";
    emit("update:selectedCredentialId", created.id);
    emit("refreshCredentials");
    emit("bind");
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Не удалось сохранить API key");
  } finally {
    localBusy.value = false;
  }
}

async function verify() {
  if (!props.selectedCredentialId) return;
  localBusy.value = true;
  emit("error", null);
  try {
    await verifyCredential(props.agentSlug, props.selectedCredentialId);
    emit("refreshCredentials");
    await loadBalance();
  } catch (error) {
    emit("error", error instanceof Error ? error.message : "Verify failed");
  } finally {
    localBusy.value = false;
  }
}
</script>

<template>
  <div class="mt-6 space-y-4 rounded-xl border border-base-300 bg-base-200/20 p-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h4 class="font-semibold">Polza.ai credential</h4>
        <p class="mt-1 text-xs text-base-content/60">
          API key хранится на backend.
          <a
            href="https://polza.ai/docs"
            class="link link-hover"
            target="_blank"
            rel="noreferrer"
          >
            Документация
          </a>
        </p>
      </div>
      <div class="text-right text-sm">
        <p class="text-xs uppercase tracking-wide text-base-content/50">Баланс</p>
        <p class="font-mono font-semibold">
          <template v-if="loadingBalance">…</template>
          <template v-else-if="balance != null">{{ balance }} ₽</template>
          <template v-else>—</template>
        </p>
      </div>
    </div>

    <label class="form-control w-full">
      <span class="label-text">Credential</span>
      <select
        class="select select-bordered select-sm w-full"
        :value="selectedCredentialId"
        @change="
          emit(
            'update:selectedCredentialId',
            ($event.target as HTMLSelectElement).value,
          )
        "
      >
        <option value="">— не выбран —</option>
        <option v-for="item in polzaCredentials" :key="item.id" :value="item.id">
          {{ item.name }}
          <template v-if="item.meta.balance_amount">
            ({{ item.meta.balance_amount }} ₽)
          </template>
        </option>
      </select>
    </label>

    <div class="flex flex-wrap gap-2">
      <button type="button" class="btn btn-sm btn-primary" @click="emit('bind')">
        Привязать credential
      </button>
      <button
        type="button"
        class="btn btn-sm"
        :disabled="!selectedCredentialId || isBusy"
        @click="verify"
      >
        Verify + баланс
      </button>
    </div>

    <label class="form-control w-full">
      <span class="label-text">Модель по умолчанию</span>
      <div class="flex flex-col gap-2 sm:flex-row">
        <input
          v-model="modelFilter"
          class="input input-bordered input-sm w-full sm:max-w-xs"
          placeholder="Фильтр моделей…"
        />
        <select v-model="selectedModel" class="select select-bordered select-sm w-full font-mono">
          <option value="">— {{ loadingModels ? "загрузка…" : "не выбрана" }} —</option>
          <option v-for="model in filteredModels" :key="model.id" :value="model.id">
            {{ model.id }}
            <template v-if="model.contextLength"> · {{ model.contextLength }} ctx</template>
          </option>
        </select>
      </div>
      <p class="mt-1 text-xs text-base-content/50">
        Сохраняется в config binding (JSON). Можно переопределить в args Action:
        <code class="font-mono">model</code>.
      </p>
    </label>

    <div class="divider my-1 text-xs">Новый API key</div>

    <label class="form-control w-full">
      <span class="label-text">API key</span>
      <input
        v-model="apiKeyInput"
        type="password"
        class="input input-bordered input-sm w-full font-mono"
        placeholder="sk-…"
        autocomplete="off"
      />
    </label>
    <label class="form-control w-full">
      <span class="label-text">Название credential</span>
      <input
        v-model="credentialName"
        class="input input-bordered input-sm w-full"
        placeholder="Production Polza"
      />
    </label>
    <button
      type="button"
      class="btn btn-sm"
      :disabled="isBusy || !apiKeyInput.trim()"
      @click="addCredential"
    >
      Сохранить API key
    </button>

    <ToolLogFeed
      class="mt-4"
      :agent-slug="agentSlug"
      tool-id="polza_ai_llm"
      :credential-id="selectedCredentialId || undefined"
      compact
      show-link-to-all
      :auto-refresh-ms="5000"
      auto-refresh-default
      empty-text="Пока нет вызовов PolzaAI_LLM"
    />
  </div>
</template>
