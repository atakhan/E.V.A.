<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useTools } from "@/features/tools/composables/useTools";
import PolzaAiPanel from "@/features/tools/components/PolzaAiPanel.vue";
import WebClientPanel from "@/features/tools/components/WebClientPanel.vue";
import ToolInstanceConfigForm from "@/features/tools/components/ToolInstanceConfigForm.vue";
import {
  createCredential,
  fetchCredentials,
  verifyCredential,
  type ToolCredential,
} from "@/features/tools/services/credentialsApi";
import type { ToolInstance } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { serializePolzaConfigNote } from "@/features/tools/utils/polzaConfig";
import { serializeWebClientConfigNote } from "@/features/tools/utils/webClientConfig";
import { agentToolsPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  instanceId: string;
}>();

const router = useRouter();
const { getInstance, updateInstance, removeInstance, setInstanceEnabled } = useTools();

const credentials = ref<ToolCredential[]>([]);
const credentialError = ref<string | null>(null);
const credentialBusy = ref(false);
const newTokenInput = ref("");
const newCredentialName = ref("Telegram bot");

const instance = computed(() => getInstance(props.agentSlug, props.instanceId));
const typeDef = computed(() =>
  instance.value ? getToolDefinition(instance.value.toolId) : null,
);
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
  () => [props.agentSlug, props.instanceId] as const,
  () => {
    if (!instance.value) {
      void router.replace(agentToolsPath(props.agentSlug));
    }
  },
  { immediate: true },
);

watch(
  () => props.agentSlug,
  () => {
    void loadCredentials();
  },
  { immediate: true },
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

function removeAndGoBack() {
  if (!instance.value) return;
  if (!confirm(`Удалить instance «${instance.value.name}»?`)) return;
  removeInstance(props.agentSlug, instance.value.id);
  void router.push(agentToolsPath(props.agentSlug));
}
</script>

<template>
  <section v-if="instance" class="space-y-4">
    <div class="flex flex-wrap items-center gap-3">
      <button
        type="button"
        class="btn btn-ghost btn-sm"
        @click="router.push(agentToolsPath(agentSlug))"
      >
        ← Tools
      </button>
      <div class="min-w-0 flex-1">
        <h2 class="truncate text-lg font-semibold">{{ instance.name }}</h2>
        <p class="font-mono text-xs text-base-content/60">
          {{ instance.toolId }} · {{ instance.id }}
        </p>
      </div>
      <label class="label cursor-pointer gap-2">
        <span class="label-text text-xs">Enabled</span>
        <input
          type="checkbox"
          class="toggle toggle-sm"
          :checked="instance.enabled"
          @change="
            setInstanceEnabled(
              agentSlug,
              instance.id,
              ($event.target as HTMLInputElement).checked,
            )
          "
        />
      </label>
      <button type="button" class="btn btn-ghost btn-sm text-error" @click="removeAndGoBack">
        Удалить
      </button>
    </div>

    <div class="rounded-2xl border border-base-300 bg-base-100 p-4 shadow-sm">
      <label class="form-control w-full max-w-md">
        <span class="label-text">Имя</span>
        <input
          class="input input-bordered input-sm w-full"
          :value="instance.name"
          @change="patchInstance({ name: ($event.target as HTMLInputElement).value })"
        />
      </label>

      <div v-if="instance.toolId !== 'web_client'" class="mt-4">
        <p class="label-text mb-2">Config</p>
        <ToolInstanceConfigForm
          :tool-type-id="instance.toolId"
          :model-value="instance.config"
          @update:model-value="patchInstance({ config: $event })"
        />
      </div>

      <PolzaAiPanel
        v-if="instance.toolId === 'polza_ai_llm'"
        class="mt-4"
        :agent-slug="agentSlug"
        :credentials="credentials.filter((item) => item.toolId === 'polza_ai_llm')"
        :selected-credential-id="instance.credentialId ?? ''"
        :config-note="configNoteForPanel(instance)"
        @update:selected-credential-id="patchInstance({ credentialId: $event || undefined })"
        @update:config-note="onConfigNoteFromPanel"
        @refresh-credentials="loadCredentials"
        @error="credentialError = $event"
      />

      <WebClientPanel
        v-else-if="instance.toolId === 'web_client'"
        class="mt-4"
        :agent-slug="agentSlug"
        :credentials="credentials.filter((item) => item.toolId === 'web_client')"
        :selected-credential-id="instance.credentialId ?? ''"
        :config-note="configNoteForPanel(instance)"
        @update:selected-credential-id="patchInstance({ credentialId: $event || undefined })"
        @update:config-note="onConfigNoteFromPanel"
        @refresh-credentials="loadCredentials"
        @error="credentialError = $event"
      />

      <div v-else-if="instance.toolId === 'telegram'" class="mt-4 space-y-3">
        <label class="form-control w-full max-w-md">
          <span class="label-text">Credential (bot token)</span>
          <select
            class="select select-bordered select-sm w-full"
            :value="instance.credentialId ?? ''"
            @change="patchInstance({ credentialId: ($event.target as HTMLSelectElement).value || undefined })"
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

      <p v-if="credentialError" class="mt-3 text-sm text-error">{{ credentialError }}</p>

      <div v-if="typeDef?.commands.length" class="mt-6 border-t border-base-300 pt-4">
        <p class="text-xs font-medium text-base-content/50">Команды типа</p>
        <ul class="mt-2 space-y-1 text-xs font-mono">
          <li v-for="command in typeDef.commands" :key="command.id">
            {{ command.id }} — {{ command.description }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
