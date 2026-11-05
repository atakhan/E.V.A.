<script setup lang="ts">
import { computed } from "vue";
import type {
  SkillDependencies,
  ToolDependencyStatus,
} from "@/features/agents/utils/agentDependencies";
import type { Skill } from "@/features/skills/types/skill";
import { agentActionPath } from "@/router/paths";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  agentSlug: string;
  skill: Skill;
  dependencies: SkillDependencies;
}>();

const emit = defineEmits<{
  close: [];
  openEditor: [];
  remove: [];
  selectKind: [toolId: string];
  selectPlugin: [instanceId: string];
}>();

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
</script>

<template>
  <aside
    class="absolute inset-y-0 right-0 z-30 flex w-[22rem] flex-col border-l border-base-300/60 bg-base-100 shadow-xl sm:w-96"
    data-canvas-ui
  >
    <header class="flex items-start justify-between gap-2 border-b border-base-300 px-4 py-3">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-wide text-base-content/50">
          {{ skill.systemRole ? "Системный навык" : "Навык" }}
        </p>
        <h2 class="mt-0.5 truncate text-base font-semibold">{{ skill.name }}</h2>
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
      <p v-if="skill.description" class="text-base-content/70">
        {{ skill.description }}
      </p>
      <p v-else class="text-base-content/50">Без описания</p>

      <section class="space-y-3">
        <p class="text-xs font-medium text-base-content/50">Что нужно навыку</p>

        <p v-if="!hasDependencies" class="text-xs text-base-content/50">
          Навык пока не вызывает Actions и не ждёт событий каналов.
        </p>

        <div v-if="dependencies.channels.length" class="space-y-1">
          <p class="text-[11px] uppercase tracking-wide text-base-content/45">Каналы</p>
          <ul class="flex flex-wrap gap-1.5">
            <li v-for="item in dependencies.channels" :key="item.instanceId || item.typeId">
              <button
                type="button"
                class="btn btn-xs gap-1.5"
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

        <div v-if="dependencies.plugins.length" class="space-y-1">
          <p class="text-[11px] uppercase tracking-wide text-base-content/45">Плагины</p>
          <ul class="flex flex-wrap gap-1.5">
            <li v-for="item in dependencies.plugins" :key="item.instanceId || item.typeId">
              <button
                type="button"
                class="btn btn-xs gap-1.5"
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

        <div v-if="dependencies.actions.length" class="space-y-1">
          <p class="text-[11px] uppercase tracking-wide text-base-content/45">Actions</p>
          <ul class="space-y-1.5">
            <li v-for="item in dependencies.actions" :key="item.actionId" class="text-xs">
              <template v-if="item.action">
                <RouterLink
                  :to="agentActionPath(agentSlug, item.actionId)"
                  class="link link-hover font-medium"
                >
                  {{ item.action.name }}
                </RouterLink>
                <p v-if="item.commands.length" class="font-mono text-[10px] text-base-content/50">
                  <span
                    v-for="(use, index) in item.commands"
                    :key="use.stepId || index"
                    :class="use.status === 'ok' ? '' : 'text-error'"
                  >{{ index > 0 ? " → " : "" }}{{ use.instanceId || "?" }}.{{ use.command }}</span>
                </p>
                <p v-else class="text-[10px] text-base-content/45">без шагов</p>
              </template>
              <p v-else class="text-error">Нет Action «{{ item.actionId }}»</p>
            </li>
          </ul>
        </div>
      </section>

      <dl class="space-y-2 text-xs">
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Версия</dt>
          <dd class="font-mono">{{ skill.version }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Состояния</dt>
          <dd>{{ skill.states.length }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Initial</dt>
          <dd class="font-mono">{{ skill.initial ?? "—" }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-base-content/50">Обновлён</dt>
          <dd>{{ formatDateTime(skill.updatedAt) }}</dd>
        </div>
      </dl>
    </div>

    <footer class="flex flex-col gap-2 border-t border-base-300 p-3">
      <button type="button" class="btn btn-sm btn-primary" @click="emit('openEditor')">
        Открыть редактор
      </button>
      <button type="button" class="btn btn-sm btn-ghost text-error" @click="emit('remove')">
        Удалить навык
      </button>
    </footer>
  </aside>
</template>
