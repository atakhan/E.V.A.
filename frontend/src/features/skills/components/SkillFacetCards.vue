<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type {
  SkillDependencies,
  ToolDependencyStatus,
} from "@/features/agents/utils/agentDependencies";
import {
  READING_STAGE_PAD,
  READING_STAGE_TYPE,
  READING_STAGE_WIDTH,
} from "@/features/constructor/utils/readingStage";
import type { Skill } from "@/features/skills/types/skill";
import {
  skillOrbitItem,
  type SkillOrbitId,
} from "@/features/skills/utils/skillOrbit";
import { agentActionPath } from "@/router/paths";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  agentSlug: string;
  skill: Skill;
  facet: SkillOrbitId;
  dependencies: SkillDependencies;
  /** Reveals with the facet layer (one-pass with center flight). */
  shown?: boolean;
}>();

const emit = defineEmits<{
  openEditor: [];
  remove: [];
  selectKind: [toolId: string];
  selectPlugin: [instanceId: string];
}>();

const meta = computed(() => skillOrbitItem(props.facet));

const STATUS_LABEL: Record<ToolDependencyStatus, string> = {
  ok: "",
  disabled: "выключен",
  unknown: "не найден",
  ambiguous: "неоднозначная ссылка",
  unimplemented: "нет реализации",
};

const hasDependencies = computed(
  () =>
    props.dependencies.actions.length > 0 ||
    props.dependencies.channels.length > 0 ||
    props.dependencies.plugins.length > 0,
);

/** Plugins with an enabled instance are on the table, even if they cannot execute. */
function pluginOnTable(status: ToolDependencyStatus): boolean {
  return status === "ok" || status === "unimplemented";
}

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

      <template v-if="facet === 'about'">
        <p class="font-medium" :style="typeBody">
          {{ skill.systemRole ? "Системный навык" : "Навык" }}
        </p>
        <p v-if="skill.description" class="text-base-content/70" :style="typeBody">
          {{ skill.description }}
        </p>
        <p v-else class="text-base-content/50" :style="typeBody">Без описания</p>
        <dl class="space-y-[0.7em]" :style="typeBody">
          <div class="flex justify-between gap-3">
            <dt class="text-base-content/50" :style="typeLabel">Версия</dt>
            <dd class="font-mono" :style="typeMono">{{ skill.version }}</dd>
          </div>
          <div class="flex justify-between gap-3">
            <dt class="text-base-content/50" :style="typeLabel">Обновлён</dt>
            <dd :style="typeLabel">{{ formatDateTime(skill.updatedAt) }}</dd>
          </div>
        </dl>
        <button
          type="button"
          class="btn btn-primary self-start"
          :style="typeLabel"
          @click="emit('openEditor')"
        >
          Открыть редактор
        </button>
        <button
          type="button"
          class="btn btn-ghost self-start text-error"
          :style="typeLabel"
          @click="emit('remove')"
        >
          Удалить навык
        </button>
      </template>

      <template v-else-if="facet === 'states'">
        <p class="font-mono text-base-content/55" :style="typeMono">
          initial: {{ skill.initial ?? "—" }}
        </p>
        <ul v-if="skill.states.length" class="space-y-[1.1em]">
          <li v-for="state in skill.states" :key="state.id">
            <p class="font-mono font-medium" :style="typeMono">
              {{ state.name || state.id }}
              <span
                v-if="skill.initial === state.id"
                class="ml-2 font-sans font-normal text-base-content/45"
                :style="typeLabel"
              >initial</span>
            </p>
            <p
              v-if="state.onEnter.length || state.transitions.length"
              class="mt-1 font-mono text-base-content/45"
              :style="typeMono"
            >
              enter {{ state.onEnter.length }} · переходов {{ state.transitions.length }}
            </p>
          </li>
        </ul>
        <p v-else class="text-base-content/50" :style="typeBody">Состояний пока нет.</p>
      </template>

      <template v-else-if="facet === 'needs'">
        <p v-if="!hasDependencies" class="text-base-content/50" :style="typeBody">
          Навык пока не вызывает Actions и не ждёт событий каналов.
        </p>

        <div v-if="dependencies.channels.length" class="space-y-[0.7em]">
          <p
            class="font-medium uppercase tracking-wide text-base-content/45"
            :style="typeEyebrow"
          >
            Каналы
          </p>
          <ul class="flex flex-wrap gap-2">
            <li v-for="item in dependencies.channels" :key="item.instanceId || item.typeId">
              <button
                type="button"
                class="btn btn-sm gap-1.5"
                :style="typeLabel"
                :disabled="item.status !== 'ok'"
                :title="item.events.length ? `ждёт ${item.events.join(', ')}` : undefined"
                @click="emit('selectKind', item.typeId)"
              >
                <span
                  class="size-1.5 rounded-full"
                  :class="item.status === 'ok' ? 'bg-success' : 'bg-error'"
                  aria-hidden="true"
                />
                {{ item.name }}
                <span v-if="STATUS_LABEL[item.status]" class="font-normal text-error">
                  {{ STATUS_LABEL[item.status] }}
                </span>
              </button>
            </li>
          </ul>
        </div>

        <div v-if="dependencies.plugins.length" class="space-y-[0.7em]">
          <p
            class="font-medium uppercase tracking-wide text-base-content/45"
            :style="typeEyebrow"
          >
            Плагины
          </p>
          <ul class="flex flex-wrap gap-2">
            <li v-for="item in dependencies.plugins" :key="item.instanceId || item.typeId">
              <button
                type="button"
                class="btn btn-sm gap-1.5"
                :style="typeLabel"
                :disabled="!pluginOnTable(item.status)"
                @click="emit('selectPlugin', item.instanceId)"
              >
                <span
                  class="size-1.5 rounded-full"
                  :class="item.status === 'ok' ? 'bg-success' : 'bg-error'"
                  aria-hidden="true"
                />
                {{ item.name }}
                <span v-if="STATUS_LABEL[item.status]" class="font-normal text-error">
                  {{ STATUS_LABEL[item.status] }}
                </span>
              </button>
            </li>
          </ul>
        </div>

        <div v-if="dependencies.actions.length" class="space-y-[0.7em]">
          <p
            class="font-medium uppercase tracking-wide text-base-content/45"
            :style="typeEyebrow"
          >
            Actions
          </p>
          <ul class="space-y-[0.9em]">
            <li v-for="item in dependencies.actions" :key="item.actionId">
              <template v-if="item.action">
                <RouterLink
                  :to="agentActionPath(agentSlug, item.actionId)"
                  class="link link-hover font-medium"
                  :style="typeBody"
                >
                  {{ item.action.name }}
                </RouterLink>
                <p
                  v-if="item.commands.length"
                  class="font-mono text-base-content/50"
                  :style="typeMono"
                >
                  <span
                    v-for="(use, index) in item.commands"
                    :key="use.stepId || index"
                    :class="use.status === 'ok' ? '' : 'text-error'"
                  >{{ index > 0 ? " → " : "" }}{{ use.instanceId || "?" }}.{{ use.command }}</span>
                </p>
                <p v-else class="text-base-content/45" :style="typeLabel">без шагов</p>
              </template>
              <p v-else class="text-error" :style="typeBody">Нет Action «{{ item.actionId }}»</p>
            </li>
          </ul>
        </div>
      </template>
    </div>
  </aside>
</template>
