<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import MemoryRecord from "@/features/memory/components/MemoryRecord.vue";
import { runStatusWord } from "@/features/memory/utils/memoryCard";
import {
  MEMORY_ATTENTION_CAPACITY,
  memoryOrbitItem,
  type MemoryOrbitId,
} from "@/features/memory/utils/memoryOrbit";
import SkillRunStatusBadge from "@/features/runtime/components/SkillRunStatusBadge.vue";
import type { AgentMemory } from "@/features/runtime/types/runtime";
import { skillRunDetailPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  facet: MemoryOrbitId;
  memory: AgentMemory | null;
  loading: boolean;
  error: string | null;
  skillNames?: Array<{ id: string; name: string }>;
  /** Burst with the facet layer (one-pass with center flight). */
  shown?: boolean;
}>();

const meta = computed(() => memoryOrbitItem(props.facet));

const activeRuns = computed(() =>
  (props.memory?.runs ?? []).filter(
    (run) => run.status === "running" || run.status === "waiting",
  ),
);

const attentionCards = computed(() => {
  const peers = props.memory?.interaction?.peers ?? [];
  const fromPeers = peers.slice(0, MEMORY_ATTENTION_CAPACITY).map((peer) => ({
    id: `peer:${peer.agentSlug}`,
    title: peer.name || peer.agentSlug,
    kind: "другой",
  }));
  const room = MEMORY_ATTENTION_CAPACITY - fromPeers.length;
  const fromRuns = activeRuns.value.slice(0, Math.max(0, room)).map((run) => ({
    id: `run:${run.skillRunId}`,
    title: run.skillId,
    kind: "задача",
  }));
  return [...fromPeers, ...fromRuns].slice(0, MEMORY_ATTENTION_CAPACITY);
});

/** Draft cards for the open shelf — empty shelves still show one placeholder card. */
const cards = computed(() => {
  if (props.error && !props.memory) {
    return [{ id: "err", kind: "состояние", title: props.error, body: "" }];
  }
  if (props.loading && !props.memory) {
    return [{ id: "load", kind: "состояние", title: "Загрузка…", body: "" }];
  }

  if (props.facet === "self") {
    return [
      {
        id: "self-empty",
        kind: "полка",
        title: "Пока пусто",
        body: "Сюда лягут устойчивые куски «кто я» — из жизни и установки навыков.",
      },
    ];
  }

  if (props.facet === "life") {
    const events = props.memory?.events ?? [];
    if (events.length === 0) {
      return [
        {
          id: "life-empty",
          kind: "жизнь",
          title: "Записей жизни ещё нет",
          body: "Main log пока пуст. Черновик: runtime-события появятся здесь.",
        },
      ];
    }
    return events.slice(0, 12).map((event) => ({
      id: event.id,
      kind: "событие",
      title: event.eventType,
      body: event.skillId,
      href: skillRunDetailPath(props.agentSlug, event.skillRunId),
    }));
  }

  if (props.facet === "outcomes") {
    return [
      {
        id: "outcomes-empty",
        kind: "веха",
        title: "Пока пусто",
        body: "Вехи появятся, когда навыки запишут их Actions работы с памятью.",
      },
    ];
  }

  if (props.facet === "tasks") {
    if (activeRuns.value.length === 0) {
      return [
        {
          id: "tasks-empty",
          kind: "задача",
          title: "Актуальных задач нет",
          body: "Черновик: активные прогоны как «сейчас в работе».",
        },
      ];
    }
    return activeRuns.value.map((run) => ({
      id: run.skillRunId,
      kind: "задача",
      title: run.skillId,
      body: `${runStatusWord(run.status)} · ${run.currentState}`,
      run,
      href: skillRunDetailPath(props.agentSlug, run.skillRunId),
    }));
  }

  if (props.facet === "others") {
    const peers = props.memory?.interaction?.peers ?? [];
    if (peers.length === 0) {
      return [
        {
          id: "others-empty",
          kind: "другой",
          title: "Других пока нет",
          body: "Связи появятся как адреса канала «Агенты» / манифест.",
        },
      ];
    }
    return peers.map((peer) => ({
      id: peer.agentSlug,
      kind: "другой",
      title: peer.name || peer.agentSlug,
      body: `/${peer.agentSlug} · вход ${peer.allowInbound ? "да" : "нет"} · выход ${peer.allowOutbound ? "да" : "нет"}`,
    }));
  }

  if (props.facet === "skills") {
    const skills = props.skillNames ?? [];
    if (skills.length === 0) {
      return [
        {
          id: "skills-empty",
          kind: "навык",
          title: "Навыков пока нет",
          body: "Куски памяти при установке навыка — следующий слой.",
        },
      ];
    }
    return skills.map((skill) => ({
      id: skill.id,
      kind: "навык",
      title: skill.name,
      body: `${skill.id} · память навыка ещё не установлена`,
    }));
  }

  if (props.facet === "focus") {
    if (attentionCards.value.length === 0) {
      return [
        {
          id: "focus-empty",
          kind: "внимание",
          title: "Зона внимания пуста",
          body: `Не больше ${MEMORY_ATTENTION_CAPACITY} карточек в фокусе.`,
        },
      ];
    }
    return attentionCards.value.map((card) => ({
      id: card.id,
      kind: card.kind,
      title: card.title,
      body: `Фокус · ${card.kind}`,
    }));
  }

  return [];
});
</script>

<template>
  <div
    class="pointer-events-auto absolute flex w-[min(20rem,calc(100vw-4rem))] flex-col gap-2 transition-[opacity,transform] duration-300 ease-out motion-reduce:transition-none"
    :style="{
      left: '9rem',
      top: '50%',
      transform: shown ? 'translateY(-50%) scale(1)' : 'translateY(-50%) scale(0.85)',
      opacity: shown ? '1' : '0',
      transformOrigin: 'left center',
      maxHeight: 'min(70vh, 32rem)',
    }"
  >
    <p class="px-1 text-[10px] uppercase tracking-wide text-base-content/45">
      {{ meta.label }}
    </p>
    <div class="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
      <article
        v-for="card in cards"
        :key="card.id"
        class="rounded-2xl border border-base-300 bg-base-100 px-3 py-2.5 shadow-sm"
      >
        <p class="text-[10px] uppercase tracking-wide text-base-content/45">{{ card.kind }}</p>
        <p class="mt-0.5 truncate text-sm font-medium">{{ card.title }}</p>
        <p v-if="card.body" class="mt-1 text-xs text-base-content/60 whitespace-pre-wrap">
          {{ card.body }}
        </p>
        <template v-if="card.run">
          <div class="mt-2 flex justify-end">
            <SkillRunStatusBadge :status="card.run.status" />
          </div>
          <div class="mt-2 space-y-2">
            <MemoryRecord title="params" :record="card.run.params" />
            <MemoryRecord title="vars" :record="card.run.vars" />
          </div>
        </template>
        <RouterLink
          v-if="card.href"
          :to="card.href"
          class="btn btn-xs btn-ghost mt-2 px-1"
        >
          Прогон
        </RouterLink>
      </article>
    </div>
  </div>
</template>
