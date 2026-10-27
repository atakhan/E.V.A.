<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { getAgentBySlug } from "@/features/agents/services/agentsStorage";
import { toolUsage, type ToolUsage } from "@/features/agents/utils/agentDependencies";
import type { WorldLinkStatus } from "@/features/agents/utils/evaluateWorldLink";
import LinkStatusNote from "@/features/constructor/components/LinkStatusNote.vue";
import ToolUsageList from "@/features/constructor/components/ToolUsageList.vue";
import PolzaAiPanel from "@/features/tools/components/PolzaAiPanel.vue";
import ToolInstanceConfigForm from "@/features/tools/components/ToolInstanceConfigForm.vue";
import { useTools } from "@/features/tools/composables/useTools";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { fetchCredentials, type ToolCredential } from "@/features/tools/services/credentialsApi";
import type { ToolInstance } from "@/features/tools/types/tool";
import { serializePolzaConfigNote } from "@/features/tools/utils/polzaConfig";
import { agentToolInstancePath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  instanceId: string;
  status: WorldLinkStatus;
  reason: string;
}>();

const emit = defineEmits<{
  close: [];
  disconnect: [];
  selectSkill: [skillId: string];
}>();

const { getInstance, updateInstance } = useTools();

const credentials = ref<ToolCredential[]>([]);
const credentialError = ref<string | null>(null);

const instance = computed(() => getInstance(props.agentSlug, props.instanceId) ?? null);
const typeDef = computed(() =>
  instance.value ? getToolDefinition(instance.value.toolId) : undefined,
);

const usage = computed((): ToolUsage => {
  const agent = getAgentBySlug(props.agentSlug);
  if (!agent) return { actions: [], skills: [] };
  return toolUsage(agent, { kind: "instance", instanceId: props.instanceId });
});

/** command id → ids of Actions calling it through this instance */
const commandUsers = computed(() => {
  const users = new Map<string, string[]>();
  for (const item of usage.value.actions) {
    for (const command of item.commands) {
      users.set(command, [...(users.get(command) ?? []), item.action.id]);
    }
  }
  return users;
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

watch(
  () => props.instanceId,
  () => {
    credentialError.value = null;
  },
);

function patchInstance(patch: Partial<ToolInstance>) {
  if (!instance.value) return;
  updateInstance(props.agentSlug, instance.value.id, patch);
}

function polzaConfigNote(item: ToolInstance): string {
  return serializePolzaConfigNote({
    model: typeof item.config.model === "string" ? item.config.model : undefined,
  });
}

function onPolzaConfigNote(note: string) {
  if (!instance.value) return;
  try {
    const parsed = JSON.parse(note) as { model?: string };
    patchInstance({ config: { ...instance.value.config, model: parsed.model } });
  } catch {
    patchInstance({ config: { ...instance.value.config, note } });
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
        <p class="text-xs uppercase tracking-wide text-base-content/50">Плагин</p>
        <h2 class="mt-0.5 truncate text-base font-semibold">{{ instance?.name ?? instanceId }}</h2>
        <p class="mt-0.5 font-mono text-[10px] text-base-content/45">
          {{ instance?.toolId ?? "?" }} · {{ instanceId }}
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
      <LinkStatusNote :status="status" :reason="reason" />

      <p v-if="typeDef?.description" class="text-xs text-base-content/60">
        {{ typeDef.description }}
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

        <div>
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
          :config-note="polzaConfigNote(instance)"
          @update:selected-credential-id="patchInstance({ credentialId: $event || undefined })"
          @update:config-note="onPolzaConfigNote"
          @refresh-credentials="loadCredentials"
          @error="credentialError = $event"
        />

        <p v-if="credentialError" class="text-sm text-error">{{ credentialError }}</p>

        <section v-if="typeDef?.commands.length" class="space-y-1.5">
          <p class="text-xs font-medium text-base-content/50">Команды</p>
          <ul class="space-y-1.5">
            <li v-for="command in typeDef.commands" :key="command.id" class="text-xs">
              <p class="font-mono">{{ command.id }}</p>
              <p v-if="command.description" class="text-base-content/55">
                {{ command.description }}
              </p>
              <p
                v-if="commandUsers.get(command.id)"
                class="font-mono text-[10px] text-base-content/45"
              >
                вызывают: {{ commandUsers.get(command.id)!.join(", ") }}
              </p>
            </li>
          </ul>
        </section>

        <ToolUsageList
          :agent-slug="agentSlug"
          :usage="usage"
          @select-skill="emit('selectSkill', $event)"
        />
      </template>

      <p v-else class="text-sm text-error">Плагин не найден</p>
    </div>

    <footer class="flex flex-col gap-2 border-t border-base-300 p-3">
      <RouterLink
        v-if="instance"
        :to="agentToolInstancePath(agentSlug, instance.id)"
        class="btn btn-sm btn-ghost"
      >
        Открыть в Tools
      </RouterLink>
      <button type="button" class="btn btn-sm btn-ghost text-error" @click="emit('disconnect')">
        Отключить плагин
      </button>
      <button type="button" class="btn btn-sm" @click="emit('close')">Готово</button>
    </footer>
  </aside>
</template>
