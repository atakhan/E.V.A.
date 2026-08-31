<script setup lang="ts">
import { computed } from "vue";
import type { SkillRunHistory } from "@/features/runtime/types/runtime";

const props = defineProps<{
  history: SkillRunHistory | null;
}>();

type TimelineEntry =
  | {
      kind: "event";
      id: string;
      title: string;
      subtitle: string;
      createdAt: string;
    }
  | {
      kind: "action";
      id: string;
      title: string;
      subtitle: string;
      createdAt: string;
    }
  | {
      kind: "tool";
      id: string;
      title: string;
      subtitle: string;
      createdAt: string;
    };

const entries = computed<TimelineEntry[]>(() => {
  if (!props.history) return [];
  const result: TimelineEntry[] = [];

  for (const event of props.history.events) {
    const transition =
      event.fromState || event.toState
        ? `${event.fromState ?? "?"} → ${event.toState ?? "?"}`
        : "event";
    result.push({
      kind: "event",
      id: `event-${event.id}`,
      title: event.eventType,
      subtitle: transition,
      createdAt: event.createdAt,
    });
  }

  for (const action of props.history.actionRuns) {
    result.push({
      kind: "action",
      id: `action-${action.id}`,
      title: `action.${action.actionId}`,
      subtitle: action.error ?? action.status,
      createdAt: "",
    });
    for (const tool of action.toolExecutions) {
      result.push({
        kind: "tool",
        id: `tool-${tool.id}`,
        title: `${tool.toolInstanceId}.${tool.command}`,
        subtitle: tool.error ?? `${tool.status}${tool.durationMs ? ` · ${tool.durationMs}ms` : ""}`,
        createdAt: "",
      });
    }
  }

  return result.sort((a, b) => {
    if (a.createdAt && b.createdAt) return a.createdAt.localeCompare(b.createdAt);
    if (a.createdAt) return -1;
    if (b.createdAt) return 1;
    return 0;
  });
});

function kindClass(kind: TimelineEntry["kind"]): string {
  if (kind === "event") return "border-info/40 bg-info/5";
  if (kind === "action") return "border-primary/40 bg-primary/5";
  return "border-secondary/40 bg-secondary/5";
}
</script>

<template>
  <div class="space-y-2">
    <p v-if="!entries.length" class="text-sm text-base-content/50">История пуста</p>
    <article
      v-for="entry in entries"
      :key="entry.id"
      class="rounded-xl border px-4 py-3"
      :class="kindClass(entry.kind)"
    >
      <div class="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p class="font-mono text-sm font-medium">{{ entry.title }}</p>
          <p class="mt-1 text-xs text-base-content/60">{{ entry.subtitle }}</p>
        </div>
        <span class="badge badge-ghost badge-xs uppercase">{{ entry.kind }}</span>
      </div>
      <p v-if="entry.createdAt" class="mt-2 text-xs text-base-content/45">
        {{ new Date(entry.createdAt).toLocaleString() }}
      </p>
    </article>
  </div>
</template>
