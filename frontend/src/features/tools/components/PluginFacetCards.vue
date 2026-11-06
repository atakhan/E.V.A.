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
import { getConfigSchema, mergeSchemaConfig } from "@/features/tools/utils/instanceConfig";
import { serializePolzaConfigNote } from "@/features/tools/utils/polzaConfig";
import {
  READING_STAGE_PAD,
  READING_STAGE_TYPE,
  READING_STAGE_WIDTH,
} from "@/features/constructor/utils/readingStage";
import {
  pluginOrbitItem,
  type PluginOrbitId,
} from "@/features/tools/utils/pluginOrbit";

const props = defineProps<{
  agentSlug: string;
  instanceId: string;
  facet: PluginOrbitId;
  status: WorldLinkStatus;
  reason: string;
  /** Reveals with the facet layer (one-pass with center flight). */
  shown?: boolean;
}>();

const emit = defineEmits<{
  selectSkill: [skillId: string];
}>();

const { getInstance, updateInstance } = useTools();
const credentials = ref<ToolCredential[]>([]);
const credentialError = ref<string | null>(null);

const instance = computed(() => getInstance(props.agentSlug, props.instanceId) ?? null);
const typeDef = computed(() =>
  instance.value ? getToolDefinition(instance.value.toolId) : undefined,
);
const meta = computed(() => pluginOrbitItem(props.facet));

const usage = computed((): ToolUsage => {
  const agent = getAgentBySlug(props.agentSlug);
  if (!agent) return { actions: [], skills: [] };
  return toolUsage(agent, { kind: "instance", instanceId: props.instanceId });
});

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

function patchInstance(patch: Partial<ToolInstance>) {
  if (!instance.value) return;
  updateInstance(props.agentSlug, instance.value.id, patch);
}

function onConfig(next: Record<string, unknown>) {
  if (!instance.value) return;
  patchInstance({
    config: mergeSchemaConfig(instance.value.config, next, getConfigSchema(instance.value.toolId)),
  });
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

const matchingCredentials = computed(() => {
  if (!instance.value) return [];
  return credentials.value.filter((item) => item.toolId === instance.value!.toolId);
});

/** Soft veil + blur: none at the left edge of the stage, strongest at the screen’s right. */
const veilMask =
  "linear-gradient(to right, transparent 0%, rgba(0,0,0,0.35) 28%, rgba(0,0,0,0.85) 62%, #000 100%)";

const stageStyle = {
  width: READING_STAGE_WIDTH,
};

const contentPadStyle = {
  paddingLeft: READING_STAGE_PAD.inlineStart,
  paddingRight: READING_STAGE_PAD.inlineEnd,
  paddingTop: READING_STAGE_PAD.blockStart,
  paddingBottom: READING_STAGE_PAD.blockEnd,
  fontSize: READING_STAGE_TYPE.body,
};

const typeEyebrow = { fontSize: READING_STAGE_TYPE.eyebrow };
const typeBody = { fontSize: READING_STAGE_TYPE.body };
const typeMono = { fontSize: READING_STAGE_TYPE.mono };
const typeLabel = { fontSize: READING_STAGE_TYPE.label };
</script>

<template>
  <aside
    class="pointer-events-none absolute inset-y-0 right-0 z-30 transition-opacity duration-300 ease-out motion-reduce:transition-none"
    :class="shown ? 'opacity-100' : 'opacity-0'"
    :style="stageStyle"
    aria-live="polite"
  >
    <!-- Atmosphere: gradient blur (left = clear, right edge = strong). No card chrome. -->
    <div
      class="pointer-events-none absolute inset-0 backdrop-blur-2xl"
      :style="{
        WebkitMaskImage: veilMask,
        maskImage: veilMask,
      }"
      aria-hidden="true"
    />
    <div
      class="pointer-events-none absolute inset-0 bg-base-100/55 dark:bg-base-300/40"
      :style="{
        WebkitMaskImage: veilMask,
        maskImage: veilMask,
      }"
      aria-hidden="true"
    />

    <!--
      Reading stage content: book ninths on the right half (recto).
      Future allowlist: typography / forms / motion only — see constructor-reading-stage-draft.md
    -->
    <div
      class="pointer-events-auto relative flex h-full flex-col gap-[1.1em] overflow-y-auto leading-relaxed text-base-content"
      :style="contentPadStyle"
    >
      <p
        class="font-medium uppercase tracking-wide text-base-content/45"
        :style="typeEyebrow"
      >
        {{ meta.label }}
      </p>
      <p class="text-base-content/60" :style="typeBody">{{ meta.shelf }}</p>

      <template v-if="!instance">
        <p class="text-error" :style="typeBody">Плагин не найден</p>
      </template>

      <template v-else-if="facet === 'about'">
        <LinkStatusNote :status="status" :reason="reason" />
        <p v-if="typeDef?.description" class="text-base-content/65" :style="typeBody">
          {{ typeDef.description }}
        </p>
        <label class="form-control w-full">
          <span class="label-text text-base-content/55" :style="typeLabel">Имя instance</span>
          <input
            class="input input-bordered w-full bg-base-100/70"
            :style="typeBody"
            :value="instance.name"
            @change="patchInstance({ name: ($event.target as HTMLInputElement).value })"
          />
        </label>
        <p class="font-mono text-base-content/45" :style="typeMono">
          {{ instance.toolId }} · {{ instanceId }}
        </p>
      </template>

      <template v-else-if="facet === 'commands'">
        <ul v-if="typeDef?.commands.length" class="space-y-[1.1em]">
          <li v-for="command in typeDef.commands" :key="command.id">
            <p class="font-mono font-medium" :style="typeMono">{{ command.id }}</p>
            <p v-if="command.description" class="mt-1 text-base-content/60" :style="typeBody">
              {{ command.description }}
            </p>
            <p
              v-if="commandUsers.get(command.id)"
              class="mt-1 font-mono text-base-content/45"
              :style="typeMono"
            >
              вызывают: {{ commandUsers.get(command.id)!.join(", ") }}
            </p>
          </li>
        </ul>
        <p v-else class="text-base-content/50" :style="typeBody">Команд в каталоге нет.</p>
      </template>

      <template v-else-if="facet === 'events'">
        <ul v-if="typeDef?.events.length" class="space-y-[1.1em]">
          <li v-for="event in typeDef.events" :key="event.id">
            <p class="font-mono font-medium" :style="typeMono">{{ event.id }}</p>
            <p v-if="event.description" class="mt-1 text-base-content/60" :style="typeBody">
              {{ event.description }}
            </p>
          </li>
        </ul>
        <p v-else class="text-base-content/50" :style="typeBody">Событий у типа нет.</p>
      </template>

      <template v-else-if="facet === 'config'">
        <div class="reading-stage-forms space-y-[1.1em]" :style="typeBody">
          <ToolInstanceConfigForm
            :tool-type-id="instance.toolId"
            :model-value="instance.config"
            @update:model-value="onConfig"
          />
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
        </div>
      </template>

      <template v-else-if="facet === 'credential'">
        <p v-if="!typeDef?.credentialKind" class="text-base-content/50" :style="typeBody">
          Этому типу секрет не нужен.
        </p>
        <template v-else>
          <label class="form-control w-full">
            <span class="label-text text-base-content/55" :style="typeLabel">Credential</span>
            <select
              class="select select-bordered w-full bg-base-100/70"
              :style="typeBody"
              :value="instance.credentialId ?? ''"
              @change="
                patchInstance({
                  credentialId: ($event.target as HTMLSelectElement).value || undefined,
                })
              "
            >
              <option value="">— не выбран —</option>
              <option v-for="item in matchingCredentials" :key="item.id" :value="item.id">
                {{ item.name || item.id }}
              </option>
            </select>
          </label>
          <p class="font-mono text-base-content/45" :style="typeMono">
            kind: {{ typeDef.credentialKind }}
          </p>
          <p v-if="credentialError" class="text-error" :style="typeBody">{{ credentialError }}</p>
        </template>
      </template>

      <template v-else-if="facet === 'usage'">
        <div :style="typeBody">
          <ToolUsageList
            :agent-slug="agentSlug"
            :usage="usage"
            @select-skill="emit('selectSkill', $event)"
          />
        </div>
      </template>
    </div>
  </aside>
</template>
