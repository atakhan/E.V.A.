<script setup lang="ts">
import type { ToolUsage } from "@/features/agents/utils/agentDependencies";
import { agentActionPath } from "@/router/paths";

defineProps<{
  agentSlug: string;
  usage: ToolUsage;
}>();

const emit = defineEmits<{
  selectSkill: [skillId: string];
}>();
</script>

<template>
  <section class="space-y-3">
    <p class="text-xs font-medium text-base-content/50">Где используется</p>

    <p
      v-if="usage.skills.length === 0 && usage.actions.length === 0"
      class="text-xs text-base-content/50"
    >
      Пока нигде: Actions агента его не вызывают, навыки не ждут его событий.
    </p>

    <div v-if="usage.skills.length" class="space-y-1">
      <p class="text-[11px] uppercase tracking-wide text-base-content/45">Навыки</p>
      <ul class="space-y-1">
        <li v-for="item in usage.skills" :key="item.skill.id">
          <button
            type="button"
            class="flex w-full flex-col items-start rounded-lg border border-base-300 px-2.5 py-1.5 text-left text-xs transition hover:border-primary/50"
            @click="emit('selectSkill', item.skill.id)"
          >
            <span class="font-medium">{{ item.skill.name }}</span>
            <span v-if="item.actionIds.length" class="font-mono text-[10px] text-base-content/50">
              через {{ item.actionIds.join(", ") }}
            </span>
            <span v-if="item.events.length" class="font-mono text-[10px] text-base-content/50">
              ждёт {{ item.events.join(", ") }}
            </span>
          </button>
        </li>
      </ul>
    </div>

    <div v-if="usage.actions.length" class="space-y-1">
      <p class="text-[11px] uppercase tracking-wide text-base-content/45">Actions</p>
      <ul class="space-y-1">
        <li
          v-for="item in usage.actions"
          :key="item.action.id"
          class="flex items-baseline justify-between gap-2 text-xs"
        >
          <RouterLink
            :to="agentActionPath(agentSlug, item.action.id)"
            class="link link-hover min-w-0 truncate"
          >
            {{ item.action.name }}
          </RouterLink>
          <span class="shrink-0 font-mono text-[10px] text-base-content/50">
            {{ item.commands.join(", ") }}
          </span>
        </li>
      </ul>
    </div>
  </section>
</template>
