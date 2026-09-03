<script setup lang="ts">
import type { BehaviorNode, CanvasMode } from "@/features/skills/types/behavior";
import type { ActionDef } from "@/features/actions/types/action";
import { worstSeverity, type SkillIssueMaps } from "@/features/skills/utils/skillIssueIndex";

const props = defineProps<{
  node: BehaviorNode;
  mode: CanvasMode;
  selected?: boolean;
  actions?: ActionDef[];
  issueMaps?: SkillIssueMaps;
  overlay?: "idle" | "done" | "active" | "todo";
}>();

const emit = defineEmits<{
  select: [];
}>();

function actionMeta(actionId: string) {
  return props.actions?.find((item) => item.id === actionId);
}

function subtitle(node: BehaviorNode): string {
  if (node.type === "wait") {
    const waitFor = node.waitFor;
    if (waitFor.type === "event") return waitFor.event;
    if (waitFor.type === "action") return `action.${waitFor.actionId}.completed`;
    if (waitFor.type === "input") return waitFor.event || "channel.message.received";
    return waitFor.expression;
  }
  if (node.type === "do") return node.actionId;
  if (node.type === "decide") return "условие";
  return "final";
}

function glyph(node: BehaviorNode): string {
  if (node.type === "wait") return "⏳";
  if (node.type === "do") return "▶";
  if (node.type === "decide") return "?";
  return "■";
}

function humanTitle(node: BehaviorNode): string {
  if (node.type === "do") {
    return actionMeta(node.actionId)?.name || node.title || node.actionId;
  }
  if (node.type === "decide") return node.question || node.title || "Если…";
  return node.title || node.id;
}
</script>

<template>
  <button
    type="button"
    class="card w-full cursor-pointer border text-left shadow-sm"
    :class="{
      'border-primary ring-2 ring-primary/30': selected,
      'border-base-300 bg-base-100': !selected && overlay !== 'active',
      'border-success': overlay === 'done',
      'border-info': overlay === 'active',
      'opacity-60': overlay === 'todo',
    }"
    @click.stop="emit('select')"
  >
    <div class="card-body gap-1 p-3">
      <div class="flex items-start justify-between gap-2">
        <p class="text-sm font-medium leading-snug">
          <span class="mr-1 opacity-70">{{ glyph(node) }}</span>
          {{ humanTitle(node) }}
        </p>
        <span
          v-if="issueMaps && worstSeverity(issueMaps.byNode.get(node.id) ?? [])"
          class="badge badge-xs"
          :class="
            worstSeverity(issueMaps.byNode.get(node.id) ?? []) === 'error'
              ? 'badge-error'
              : 'badge-warning'
          "
        />
      </div>
      <p v-if="node.type === 'do'" class="text-xs text-base-content/60">
        {{ actionMeta(node.actionId)?.description || "Действие агента" }}
      </p>
      <p v-if="mode === 'logic'" class="font-mono text-[10px] text-base-content/45">
        {{ subtitle(node) }}
      </p>
      <p
        v-else-if="node.type === 'do'"
        class="font-mono text-[10px] text-base-content/40"
      >
        {{ node.actionId }}
      </p>
      <div v-if="overlay && overlay !== 'idle'" class="mt-1">
        <span v-if="overlay === 'done'" class="badge badge-xs badge-success">✓</span>
        <span v-else-if="overlay === 'active'" class="badge badge-xs badge-info">● выполняется</span>
        <span v-else class="badge badge-xs badge-ghost">○</span>
      </div>
    </div>
  </button>
</template>
