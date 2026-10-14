<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { WorldLinkStatus } from "@/features/agents/utils/evaluateWorldLink";
import PolzaAiPanel from "@/features/tools/components/PolzaAiPanel.vue";
import ToolInstanceConfigForm from "@/features/tools/components/ToolInstanceConfigForm.vue";
import { useTools } from "@/features/tools/composables/useTools";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import {
  createCredential,
  fetchCredentials,
  verifyCredential,
  type ToolCredential,
} from "@/features/tools/services/credentialsApi";
import type { ToolInstance } from "@/features/tools/types/tool";
import { serializePolzaConfigNote } from "@/features/tools/utils/polzaConfig";
import { serializeWebClientConfigNote } from "@/features/tools/utils/webClientConfig";

const props = defineProps<{
  agentSlug: string;
  toolId: string;
  status: WorldLinkStatus;
  reason: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { getInstancesByType, updateInstance } = useTools();

const credentials = ref<ToolCredential[]>([]);
const credentialError = ref<string | null>(null);
const credentialBusy = ref(false);
const newTokenInput = ref("");
const newCredentialName = ref("Telegram bot");

const instance = computed(() => {
  const items = getInstancesByType(props.agentSlug, props.toolId);
  return items.find((item) => item.enabled) ?? items[0] ?? null;
});

const typeDef = computed(() => getToolDefinition(props.toolId));

const telegramCredentials = computed(() =>
  credentials.value.filter((item) => item.toolId === "telegram"),
);

async function loadCredentials() {
  try {
    credentials.value = await fetchCredentials(props.agentSlug);
  } catch {
    credentials.value = [];
  }
}

watch(
  () => props.agentSlug,
  () => {
    void loadCredentials();
  },
  { immediate: true },
);

watch(
  () => props.toolId,
  () => {
    credentialError.value = null;
    newTokenInput.value = "";
  },
);

onMounted(() => {
  void loadCredentials();
});

function patchInstance(patch: Partial<ToolInstance>) {
  if (!instance.value) return;
  updateInstance(props.agentSlug, instance.value.id, patch);
}

function configNoteForPanel(item: ToolInstance): string {
  if (item.toolId === "polza_ai_llm") {
    return serializePolzaConfigNote({
      model: typeof item.config.model === "string" ? item.config.model : undefined,
    });
  }
  if (item.toolId === "web_client") {
    return serializeWebClientConfigNote(
      item.config as Parameters<typeof serializeWebClientConfigNote>[0],
    );
  }
  return JSON.stringify(item.config);
}

function onConfigNoteFromPanel(note: string) {
  if (!instance.value) return;
  if (instance.value.toolId === "polza_ai_llm") {
    try {
      const parsed = JSON.parse(note) as { model?: string };
      patchInstance({ config: { ...instance.value.config, model: parsed.model } });
    } catch {
      patchInstance({ config: { ...instance.value.config, note } });
    }
    return;
  }
  if (instance.value.toolId === "web_client") {
    try {
      patchInstance({ config: JSON.parse(note) as Record<string, unknown> });
    } catch {
      return;
    }
  }
}

async function createTelegramCredential() {
  credentialError.value = null;
  const token = newTokenInput.value.trim();
  if (!token) {
    credentialError.value = "Введите bot token";
    return;
  }
  credentialBusy.value = true;
  try {
    const credential = await createCredential(props.agentSlug, {
      toolId: "telegram",
      name: newCredentialName.value.trim() || "Telegram bot",
      botToken: token,
    });
    await loadCredentials();
    if (instance.value?.toolId === "telegram") {
      patchInstance({ credentialId: credential.id });
    }
    newTokenInput.value = "";
  } catch (error) {
    credentialError.value = error instanceof Error ? error.message : "Ошибка создания credential";
  } finally {
    credentialBusy.value = false;
  }
}

async function verifyTelegramCredential() {
  if (!instance.value?.credentialId) return;
  credentialBusy.value = true;
  credentialError.value = null;
  try {
    await verifyCredential(props.agentSlug, instance.value.credentialId);
  } catch (error) {
    credentialError.value = error instanceof Error ? error.message : "Проверка не удалась";
  } finally {
    credentialBusy.value = false;
  }
}
</script>

<template>
  <aside
    class="absolute inset-y-0 right-0 z-30 flex w-[22rem] flex-col border-l border-base-300/60 bg-base-100 shadow-xl sm:w-96"
    data-canvas-ui
  >
    <header class="flex items-start justify-between gap-2 border-b border-base-300 px-4 py-3">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-wide text-base-content/50">Канал</p>
        <h2 class="mt-0.5 truncate text-base font-semibold">
          {{ typeDef?.name ?? toolId }}
        </h2>
        <p class="mt-0.5 font-mono text-[10px] text-base-content/45">{{ toolId }}</p>
      </div>
      <button
        type="button"
        class="btn btn-xs btn-square btn-ghost shrink-0"
        aria-label="Закрыть"
        @click="emit('close')"
      >
        ✕
      </button>
    </header>

    <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 text-sm">
      <div
        class="rounded-xl border px-3 py-2 text-xs text-base-content/80"
        :class="{
          'border-error/40 bg-error/10': status === 'red',
          'border-warning/40 bg-warning/10': status === 'yellow',
          'border-success/40 bg-success/10': status === 'green',
          'border-base-300 bg-base-200/50': status === 'off',
        }"
        :title="status"
      >
        <p>{{ reason }}</p>
      </div>

      <p class="text-xs text-base-content/55">
        Настройка канала связи. Адреса (конкретные места) задаются отдельно слева от канала.
      </p>

      <template v-if="instance">
        <label class="form-control w-full">
          <span class="label-text text-xs">Имя instance</span>
          <input
            class="input input-bordered input-sm w-full"
            :value="instance.name"
            @change="patchInstance({ name: ($event.target as HTMLInputElement).value })"
          />
        </label>

        <div v-if="instance.toolId === 'web_client'" class="space-y-3">
          <p class="text-xs leading-snug text-base-content/60">
            Канал задаёт общий договор с веб-приложениями. Каждое приложение — адрес слева:
            свой URL и свои ключи.
          </p>
          <div>
            <p class="label-text mb-2 text-xs">Общий контракт</p>
            <ToolInstanceConfigForm
              :tool-type-id="instance.toolId"
              :model-value="instance.config"
              @update:model-value="patchInstance({ config: $event })"
            />
          </div>
        </div>

        <div v-else-if="instance.toolId !== 'web_client'">
          <p class="label-text mb-2 text-xs">Config</p>
          <ToolInstanceConfigForm
            :tool-type-id="instance.toolId"
            :model-value="instance.config"
            @update:model-value="patchInstance({ config: $event })"
          />
        </div>

        <PolzaAiPanel
          v-if="instance.toolId === 'polza_ai_llm'"
          :agent-slug="agentSlug"
          :credentials="credentials.filter((item) => item.toolId === 'polza_ai_llm')"
          :selected-credential-id="instance.credentialId ?? ''"
          :config-note="configNoteForPanel(instance)"
          @update:selected-credential-id="patchInstance({ credentialId: $event || undefined })"
          @update:config-note="onConfigNoteFromPanel"
          @refresh-credentials="loadCredentials"
          @error="credentialError = $event"
        />

        <div v-else-if="instance.toolId === 'telegram'" class="space-y-3">
          <label class="form-control w-full">
            <span class="label-text text-xs">Credential (bot token)</span>
            <select
              class="select select-bordered select-sm w-full"
              :value="instance.credentialId ?? ''"
              @change="
                patchInstance({
                  credentialId: ($event.target as HTMLSelectElement).value || undefined,
                })
              "
            >
              <option value="">— не выбран —</option>
              <option v-for="cred in telegramCredentials" :key="cred.id" :value="cred.id">
                {{ cred.name }}
              </option>
            </select>
          </label>
          <button
            type="button"
            class="btn btn-xs"
            :disabled="!instance.credentialId || credentialBusy"
            @click="verifyTelegramCredential"
          >
            Проверить token
          </button>
          <div class="rounded-xl border border-dashed border-base-300 p-3">
            <p class="text-xs font-medium">Новый bot token</p>
            <input
              v-model="newCredentialName"
              class="input input-bordered input-sm mt-2 w-full"
              placeholder="Имя credential"
            />
            <input
              v-model="newTokenInput"
              class="input input-bordered input-sm mt-2 w-full font-mono"
              placeholder="123456:ABC..."
            />
            <button
              type="button"
              class="btn btn-xs mt-2"
              :disabled="credentialBusy"
              @click="createTelegramCredential"
            >
              Создать credential
            </button>
          </div>
        </div>

        <p v-if="credentialError" class="text-sm text-error">{{ credentialError }}</p>
      </template>

      <p v-else class="text-sm text-error">Канал не найден</p>
    </div>

    <footer class="border-t border-base-300 p-3">
      <button type="button" class="btn btn-sm btn-ghost w-full" @click="emit('close')">
        Готово
      </button>
    </footer>
  </aside>
</template>
