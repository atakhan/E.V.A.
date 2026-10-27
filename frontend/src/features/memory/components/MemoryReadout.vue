<script setup lang="ts">
import { RouterLink } from "vue-router";
import MemoryRecord from "@/features/memory/components/MemoryRecord.vue";
import { runStatusWord } from "@/features/memory/utils/memoryCard";
import SkillRunStatusBadge from "@/features/runtime/components/SkillRunStatusBadge.vue";
import type { AgentMemory } from "@/features/runtime/types/runtime";
import { skillRunDetailPath } from "@/router/paths";

defineProps<{
  agentSlug: string;
  memory: AgentMemory | null;
  loading: boolean;
  error: string | null;
}>();

function when(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

function transition(fromState: string | null, toState: string | null): string {
  if (fromState && toState) return `${fromState} → ${toState}`;
  return toState ?? fromState ?? "";
}

function hasPayload(payload: Record<string, unknown>): boolean {
  return Object.keys(payload).length > 0;
}
</script>

<template>
  <div class="space-y-6">
    <p v-if="error && !memory" class="rounded-xl border border-error/40 bg-error/5 px-4 py-3 text-sm text-error">
      {{ error }}
    </p>
    <p v-else-if="loading && !memory" class="text-sm text-base-content/50">Загрузка…</p>

    <template v-else-if="memory">
      <section class="space-y-2" aria-labelledby="memory-history">
        <h3 id="memory-history" class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
          История событий
        </h3>
        <p v-if="memory.events.length === 0" class="text-sm text-base-content/60">
          Событий ещё не было. Они появятся, когда агент начнёт прогон.
        </p>
        <ol v-else class="space-y-2">
          <li
            v-for="event in memory.events"
            :key="event.id"
            class="rounded-2xl border border-base-300 bg-base-100 px-3 py-2.5"
          >
            <div class="flex flex-wrap items-baseline justify-between gap-2">
              <p class="font-mono text-sm">{{ event.eventType }}</p>
              <time class="text-[11px] text-base-content/45" :datetime="event.createdAt">
                {{ when(event.createdAt) }}
              </time>
            </div>
            <p class="mt-1 text-xs text-base-content/60">
              {{ event.skillId }}
              <span v-if="transition(event.fromState, event.toState)" class="font-mono">
                · {{ transition(event.fromState, event.toState) }}
              </span>
            </p>
            <details v-if="hasPayload(event.payload)" class="collapse collapse-arrow mt-1 bg-base-200">
              <summary class="collapse-title min-h-0 px-3 py-2 text-xs">Данные события</summary>
              <div class="collapse-content px-3 text-xs">
                <pre class="overflow-x-auto font-mono whitespace-pre-wrap">{{ JSON.stringify(event.payload, null, 2) }}</pre>
              </div>
            </details>
            <RouterLink
              :to="skillRunDetailPath(agentSlug, event.skillRunId)"
              class="btn btn-xs btn-ghost mt-1 px-1"
            >
              Прогон
            </RouterLink>
          </li>
        </ol>
      </section>

      <section class="space-y-2" aria-labelledby="memory-working">
        <h3 id="memory-working" class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
          Рабочее состояние
        </h3>
        <p v-if="memory.runs.length === 0" class="text-sm text-base-content/60">Прогонов ещё не было.</p>
        <ol v-else class="space-y-2">
          <li
            v-for="run in memory.runs"
            :key="run.skillRunId"
            class="rounded-2xl border border-base-300 bg-base-100 px-3 py-2.5"
          >
            <div class="flex flex-wrap items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="truncate font-mono text-sm">{{ run.skillId }}</p>
                <p class="mt-0.5 text-xs text-base-content/60">
                  {{ runStatusWord(run.status) }} ·
                  <span class="font-mono">{{ run.currentState }}</span>
                </p>
              </div>
              <SkillRunStatusBadge :status="run.status" />
            </div>
            <p v-if="run.conversationId" class="mt-1 truncate font-mono text-[11px] text-base-content/45">
              {{ run.conversationId }}
            </p>
            <p v-if="run.error" class="mt-2 text-sm text-error">{{ run.error }}</p>
            <div class="mt-3 space-y-3">
              <MemoryRecord title="params" :record="run.params" />
              <MemoryRecord title="vars" :record="run.vars" />
            </div>
            <RouterLink
              :to="skillRunDetailPath(agentSlug, run.skillRunId)"
              class="btn btn-xs btn-ghost mt-2 px-1"
            >
              Прогон
            </RouterLink>
          </li>
        </ol>
      </section>
    </template>

    <p v-else class="text-sm text-base-content/50">Runtime не отвечает</p>
  </div>
</template>
