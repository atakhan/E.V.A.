<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useTools } from "@/features/tools/composables/useTools";
import {
  createCredential,
  fetchCredentials,
  verifyCredential,
  type ToolCredential,
} from "@/features/tools/services/credentialsApi";
import type { ToolDefinition } from "@/features/tools/types/tool";

const props = defineProps<{
  agentSlug: string;
}>();

const {
  catalog,
  getBinding,
  isToolEnabled,
  setToolEnabled,
  updateConfigNote,
  updateCredentialId,
} = useTools();

const selectedId = ref<string>(catalog[0]?.id ?? "");
const configDraft = ref("");
const credentials = ref<ToolCredential[]>([]);
const selectedCredentialId = ref("");
const newTokenInput = ref("");
const newCredentialName = ref("Telegram bot");
const credentialError = ref<string | null>(null);
const credentialBusy = ref(false);

const selected = computed(
  () => catalog.find((tool) => tool.id === selectedId.value) ?? null,
);

const binding = computed(() =>
  selected.value ? getBinding(props.agentSlug, selected.value.id) : undefined,
);

const enabledCount = computed(
  () => catalog.filter((tool) => isToolEnabled(props.agentSlug, tool.id)).length,
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
  [selected, binding],
  () => {
    configDraft.value = binding.value?.configNote ?? "";
    selectedCredentialId.value = binding.value?.credentialId ?? "";
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

function toggle(tool: ToolDefinition, enabled: boolean) {
  setToolEnabled(props.agentSlug, tool.id, enabled);
}

function saveConfig() {
  if (!selected.value) return;
  updateConfigNote(props.agentSlug, selected.value.id, configDraft.value);
}

function saveCredentialBinding() {
  if (!selected.value) return;
  updateCredentialId(
    props.agentSlug,
    selected.value.id,
    selectedCredentialId.value || undefined,
  );
}

async function addTelegramCredential() {
  if (!newTokenInput.value.trim()) return;
  credentialBusy.value = true;
  credentialError.value = null;
  try {
    const created = await createCredential(props.agentSlug, {
      toolId: "telegram",
      name: newCredentialName.value.trim() || "Telegram bot",
      botToken: newTokenInput.value.trim(),
    });
    credentials.value = await fetchCredentials(props.agentSlug);
    selectedCredentialId.value = created.id;
    newTokenInput.value = "";
    updateCredentialId(props.agentSlug, "telegram", created.id);
  } catch (error) {
    credentialError.value = error instanceof Error ? error.message : "Не удалось сохранить credential";
  } finally {
    credentialBusy.value = false;
  }
}

async function verifySelectedCredential() {
  const id = binding.value?.credentialId;
  if (!id) return;
  credentialBusy.value = true;
  credentialError.value = null;
  try {
    const verified = await verifyCredential(props.agentSlug, id);
    credentials.value = credentials.value.map((item) => (item.id === id ? verified : item));
  } catch (error) {
    credentialError.value = error instanceof Error ? error.message : "Verify failed";
  } finally {
    credentialBusy.value = false;
  }
}
</script>

<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Tools</h2>
        <p class="text-sm text-base-content/60">
          Capabilities агента: Commands, Events и опциональные States
        </p>
      </div>
      <p class="text-sm text-base-content/50">
        Подключено {{ enabledCount }} / {{ catalog.length }}
      </p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside class="rounded-2xl border border-base-300 bg-base-100 p-2 shadow-sm">
        <button
          v-for="tool in catalog"
          :key="tool.id"
          type="button"
          class="btn btn-sm mb-1 w-full justify-start font-normal"
          :class="{ 'btn-active': selectedId === tool.id }"
          @click="selectedId = tool.id"
        >
          <span class="flex min-w-0 flex-1 items-center justify-between gap-2">
            <span class="truncate text-left">
              <span class="block truncate">{{ tool.name }}</span>
              <span class="block truncate font-mono text-[10px] opacity-60">{{ tool.id }}</span>
            </span>
            <span
              class="badge badge-xs shrink-0"
              :class="isToolEnabled(agentSlug, tool.id) ? 'badge-success' : 'badge-ghost'"
            >
              {{ isToolEnabled(agentSlug, tool.id) ? "on" : "off" }}
            </span>
          </span>
        </button>
      </aside>

      <div v-if="selected" class="space-y-4">
        <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 class="text-lg font-semibold">{{ selected.name }}</h3>
              <p class="mt-1 font-mono text-xs text-base-content/50">{{ selected.id }}</p>
              <p class="mt-3 max-w-2xl text-sm text-base-content/70">
                {{ selected.description }}
              </p>
            </div>
            <label class="label cursor-pointer gap-3">
              <span class="label-text">Подключён</span>
              <input
                type="checkbox"
                class="toggle toggle-sm"
                :checked="isToolEnabled(agentSlug, selected.id)"
                @change="
                  toggle(selected, ($event.target as HTMLInputElement).checked)
                "
              />
            </label>
          </div>

          <label class="form-control mt-4 w-full">
            <span class="label-text">Заметки / config (без секретов)</span>
            <textarea
              v-model="configDraft"
              class="textarea textarea-bordered textarea-sm w-full"
              rows="2"
              placeholder="Профиль подключения, chat defaults…"
            />
          </label>
          <div class="mt-2 flex justify-end">
            <button type="button" class="btn btn-sm" @click="saveConfig">
              Сохранить заметки
            </button>
          </div>

          <div v-if="selected.id === 'telegram'" class="mt-6 space-y-3 rounded-xl border border-base-300 bg-base-200/20 p-4">
            <h4 class="font-semibold">Telegram credential</h4>
            <p class="text-xs text-base-content/60">
              Bot token хранится на бекенде и не попадает в draft агента.
            </p>

            <label class="form-control w-full">
              <span class="label-text">Выбрать credential</span>
              <select v-model="selectedCredentialId" class="select select-bordered select-sm w-full">
                <option value="">— не выбран —</option>
                <option v-for="item in telegramCredentials" :key="item.id" :value="item.id">
                  {{ item.name }}
                  <template v-if="item.meta.bot_username"> (@{{ item.meta.bot_username }})</template>
                </option>
              </select>
            </label>

            <div class="flex flex-wrap gap-2">
              <button type="button" class="btn btn-sm btn-primary" @click="saveCredentialBinding">
                Привязать credential
              </button>
              <button
                type="button"
                class="btn btn-sm"
                :disabled="!binding?.credentialId || credentialBusy"
                @click="verifySelectedCredential"
              >
                Verify bot
              </button>
            </div>

            <label class="form-control w-full">
              <span class="label-text">Новый bot token</span>
              <input
                v-model="newTokenInput"
                type="password"
                class="input input-bordered input-sm w-full font-mono"
                placeholder="123456:ABC..."
              />
            </label>
            <label class="form-control w-full">
              <span class="label-text">Название credential</span>
              <input
                v-model="newCredentialName"
                class="input input-bordered input-sm w-full"
                placeholder="Production bot"
              />
            </label>
            <button
              type="button"
              class="btn btn-sm"
              :disabled="credentialBusy || !newTokenInput.trim()"
              @click="addTelegramCredential"
            >
              Сохранить token как credential
            </button>
            <p v-if="credentialError" class="text-sm text-error">{{ credentialError }}</p>
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
            <h4 class="font-semibold">Commands</h4>
            <p class="mt-1 text-xs text-base-content/50">Что Action может вызвать</p>
            <ul class="mt-3 space-y-2">
              <li
                v-for="command in selected.commands"
                :key="command.id"
                class="rounded-lg border border-base-300 bg-base-200/30 px-3 py-2"
              >
                <p class="font-mono text-sm">{{ selected.id }}.{{ command.id }}</p>
                <p class="mt-1 text-xs text-base-content/60">{{ command.description }}</p>
              </li>
            </ul>
          </section>

          <section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
            <h4 class="font-semibold">Events</h4>
            <p class="mt-1 text-xs text-base-content/50">Что Tool может породить</p>
            <ul v-if="selected.events.length" class="mt-3 space-y-2">
              <li
                v-for="event in selected.events"
                :key="event.id"
                class="rounded-lg border border-base-300 bg-base-200/30 px-3 py-2"
              >
                <p class="font-mono text-sm">{{ event.id }}</p>
                <p class="mt-1 text-xs text-base-content/60">{{ event.description }}</p>
              </li>
            </ul>
            <p v-else class="mt-3 text-sm text-base-content/50">Нет исходящих events</p>
          </section>
        </div>

        <section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
          <h4 class="font-semibold">States</h4>
          <p class="mt-1 text-xs text-base-content/50">
            Опциональный жизненный цикл Tool (не FSM Skill)
          </p>
          <div v-if="selected.states.length" class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="state in selected.states"
              :key="state"
              class="badge badge-outline"
            >
              {{ state }}
            </span>
          </div>
          <p v-else class="mt-3 text-sm text-base-content/50">
            У этого Tool нет собственного состояния
          </p>
        </section>
      </div>
    </div>
  </section>
</template>
