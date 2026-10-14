<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { getAgentBySlug } from "@/features/agents/services/agentsStorage";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import WebClientPanel from "@/features/tools/components/WebClientPanel.vue";
import {
  fetchCredentials,
  type ToolCredential,
} from "@/features/tools/services/credentialsApi";

const props = defineProps<{
  agentSlug: string;
  addressId: string;
}>();

const emit = defineEmits<{
  close: [];
  update: [
    patch: {
      name?: string;
      credentialId?: string;
      config?: Record<string, unknown>;
    },
  ];
  remove: [];
}>();

/** Place-specific fields per world kind (address.config). */
const PLACE_FIELDS: Record<
  string,
  Array<{ id: string; label: string; placeholder?: string }>
> = {
  telegram: [{ id: "chat_id", label: "Chat ID", placeholder: "-100…" }],
};

const credentials = ref<ToolCredential[]>([]);
const credentialError = ref<string | null>(null);

const address = computed(() => {
  const agent = getAgentBySlug(props.agentSlug);
  return agent?.world?.addresses.find((item) => item.id === props.addressId) ?? null;
});

const typeDef = computed(() =>
  address.value ? getToolDefinition(address.value.toolId) : null,
);

const placeFields = computed(() =>
  address.value ? (PLACE_FIELDS[address.value.toolId] ?? []) : [],
);

const kindCredentials = computed(() => {
  if (!address.value) return [] as ToolCredential[];
  return credentials.value.filter((item) => item.toolId === address.value!.toolId);
});

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

onMounted(() => {
  void loadCredentials();
});

function patchName(value: string) {
  emit("update", { name: value });
}

function patchCredential(value: string) {
  emit("update", { credentialId: value || undefined });
}

function patchConfigField(fieldId: string, value: string) {
  if (!address.value) return;
  const next = { ...(address.value.config ?? {}), [fieldId]: value };
  emit("update", { config: next });
}

function configString(fieldId: string): string {
  const raw = address.value?.config?.[fieldId];
  return typeof raw === "string" ? raw : raw != null ? String(raw) : "";
}
</script>

<template>
  <aside
    class="absolute inset-y-0 right-0 z-30 flex w-[22rem] flex-col border-l border-base-300/60 bg-base-100 shadow-xl sm:w-96"
    data-canvas-ui
  >
    <header class="flex items-start justify-between gap-2 border-b border-base-300 px-4 py-3">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-wide text-base-content/50">Адрес</p>
        <h2 class="mt-0.5 truncate text-base font-semibold">
          {{ address?.name ?? "Адрес" }}
        </h2>
        <p class="mt-0.5 font-mono text-[10px] text-base-content/45">
          {{ typeDef?.name ?? address?.toolId }} · место в мире
        </p>
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
      <p class="text-xs text-base-content/55">
        {{
          address?.toolId === "web_client"
            ? "Одно веб-приложение на этом канале. Сессия появляется, когда человек открывает приложение."
            : "Конкретное место в этом канале. Ключи канала настраиваются отдельно, по кабелю."
        }}
      </p>

      <template v-if="address">
        <label class="form-control w-full">
          <span class="label-text text-xs">Название</span>
          <input
            class="input input-bordered input-sm w-full"
            :value="address.name"
            @change="patchName(($event.target as HTMLInputElement).value)"
          />
        </label>

        <WebClientPanel
          v-if="address.toolId === 'web_client'"
          mode="app"
          :agent-slug="agentSlug"
          :credentials="kindCredentials"
          :selected-credential-id="address.credentialId ?? ''"
          config-note=""
          @update:selected-credential-id="patchCredential"
          @refresh-credentials="loadCredentials"
          @error="credentialError = $event"
        />
        <p v-if="address.toolId === 'web_client' && credentialError" class="text-sm text-error">
          {{ credentialError }}
        </p>

        <div v-for="field in placeFields" :key="field.id" class="form-control w-full">
          <span class="label-text text-xs">{{ field.label }}</span>
          <input
            class="input input-bordered input-sm w-full font-mono"
            :placeholder="field.placeholder"
            :value="configString(field.id)"
            @change="
              patchConfigField(field.id, ($event.target as HTMLInputElement).value.trim())
            "
          />
        </div>

        <label v-if="address.toolId !== 'web_client' && kindCredentials.length" class="form-control w-full">
          <span class="label-text text-xs">Credential адреса (опционально)</span>
          <select
            class="select select-bordered select-sm w-full"
            :value="address.credentialId ?? ''"
            @change="patchCredential(($event.target as HTMLSelectElement).value)"
          >
            <option value="">— из канала —</option>
            <option v-for="cred in kindCredentials" :key="cred.id" :value="cred.id">
              {{ cred.name }}
            </option>
          </select>
          <span class="label-text-alt mt-1 text-base-content/45">
            Если пусто — используется ключ подключённого канала.
          </span>
        </label>
      </template>

      <p v-else class="text-sm text-error">Адрес не найден</p>
    </div>

    <footer class="flex flex-col gap-2 border-t border-base-300 p-3">
      <button type="button" class="btn btn-sm btn-ghost w-full" @click="emit('close')">
        Готово
      </button>
      <button type="button" class="btn btn-sm btn-ghost text-error w-full" @click="emit('remove')">
        Удалить адрес
      </button>
    </footer>
  </aside>
</template>
