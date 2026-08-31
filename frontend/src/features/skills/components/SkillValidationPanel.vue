<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import type { AgentIssue } from "@/features/agents/utils/validateAgent";
import type { FsmSelection } from "@/features/skills/types/fsm";
import { agentActionPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  issues: AgentIssue[];
  selection?: FsmSelection | null;
  compact?: boolean;
}>();

const emit = defineEmits<{
  selectIssue: [issue: AgentIssue];
}>();

const router = useRouter();

const errors = computed(() => props.issues.filter((issue) => issue.severity === "error"));
const warnings = computed(() => props.issues.filter((issue) => issue.severity === "warning"));

function severityClass(severity: AgentIssue["severity"]): string {
  if (severity === "error") return "text-error";
  if (severity === "warning") return "text-warning";
  return "text-base-content/60";
}

function openAction(actionId: string) {
  void router.push(agentActionPath(props.agentSlug, actionId));
}

function createAction(actionId: string) {
  void router.push(agentActionPath(props.agentSlug, undefined, actionId));
}

function onIssueClick(issue: AgentIssue) {
  emit("selectIssue", issue);
}
</script>

<template>
  <section class="space-y-2" :class="compact ? 'text-xs' : 'text-sm'">
    <div v-if="!issues.length" class="rounded-lg border border-success/30 bg-success/5 px-3 py-2 text-success">
      Ошибок валидации нет
    </div>

    <div v-if="errors.length" class="space-y-1">
      <p class="text-[10px] font-semibold uppercase tracking-wide text-error">
        Errors ({{ errors.length }})
      </p>
      <ul class="space-y-1">
        <li
          v-for="issue in errors"
          :key="issue.id"
          class="rounded-lg border border-error/30 bg-error/5 px-2 py-1.5"
        >
          <button
            type="button"
            class="w-full text-left"
            @click="onIssueClick(issue)"
          >
            <span :class="severityClass(issue.severity)">{{ issue.message }}</span>
          </button>
          <div v-if="issue.code === 'unknown_action' && issue.actionId" class="mt-1 flex flex-wrap gap-1">
            <button
              type="button"
              class="btn btn-ghost btn-xs"
              @click.stop="openAction(issue.actionId!)"
            >
              Открыть Action
            </button>
            <button
              type="button"
              class="btn btn-ghost btn-xs"
              @click.stop="createAction(issue.actionId!)"
            >
              Создать Action
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div v-if="warnings.length" class="space-y-1">
      <p class="text-[10px] font-semibold uppercase tracking-wide text-warning">
        Warnings ({{ warnings.length }})
      </p>
      <ul class="space-y-1">
        <li
          v-for="issue in warnings"
          :key="issue.id"
          class="rounded-lg border border-warning/30 bg-warning/5 px-2 py-1.5"
        >
          <button
            type="button"
            class="w-full text-left"
            @click="onIssueClick(issue)"
          >
            <span :class="severityClass(issue.severity)">{{ issue.message }}</span>
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>
