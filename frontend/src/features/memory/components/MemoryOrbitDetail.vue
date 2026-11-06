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
  /** Skill names on this agent — for the skills shelf draft. */
  skillNames?: Array<{ id: string; name: string }>;
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
</script>

<template>
  <div
    class="flex max-h-[min(28rem,55vh)] min-h-0 w-[min(24rem,calc(100vw-3rem))] flex-col overflow-hidden rounded-2xl border border-base-300 bg-base-100 shadow-xl"
  >
    <header class="border-b border-base-300 px-4 py-3">
      <p class="text-xs uppercase tracking-wide text-base-content/50">
        Память · {{ meta.role === "attention" ? "сцена" : "полка" }}
      </p>
      <h2 class="mt-0.5 text-sm font-semibold">{{ meta.label }}</h2>
      <p class="mt-1 text-xs text-base-content/55">{{ meta.shelf }}</p>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto px-4 py-3 text-sm">
      <p v-if="error && !memory" class="text-error">{{ error }}</p>
      <p v-else-if="loading && !memory" class="text-base-content/50">Загрузка…</p>

      <!-- 1. Self -->
      <template v-else-if="facet === 'self'">
        <p class="rounded-xl border border-dashed border-base-300 px-3 py-4 text-base-content/60">
          Полка пустая. Сюда позже лягут устойчивые куски «кто я» — из жизни и из установки
          навыков.
        </p>
      </template>

      <!-- 2. Life log — provisional: runtime events as the stem -->
      <template v-else-if="facet === 'life'">
        <p class="mb-3 text-xs text-base-content/50">
          Черновик main log: пока показываем поток runtime-событий. Отдельный канал жизни —
          следующий слой.
        </p>
        <p v-if="!memory || memory.events.length === 0" class="text-base-content/60">
          Записей жизни ещё нет.
        </p>
        <ol v-else class="space-y-2">
          <li
            v-for="event in memory.events.slice(0, 12)"
            :key="event.id"
            class="rounded-xl border border-base-300 px-3 py-2"
          >
            <p class="font-mono text-sm">{{ event.eventType }}</p>
            <p class="mt-0.5 text-xs text-base-content/60">{{ event.skillId }}</p>
            <RouterLink
              :to="skillRunDetailPath(agentSlug, event.skillRunId)"
              class="btn btn-xs btn-ghost mt-1 px-1"
            >
              Прогон
            </RouterLink>
          </li>
        </ol>
      </template>

      <!-- 3. Outcomes — only skill-written -->
      <template v-else-if="facet === 'outcomes'">
        <p class="rounded-xl border border-dashed border-base-300 px-3 py-4 text-base-content/60">
          Полка пустая. Вехи появятся, когда навыки начнут писать в память своими Actions —
          не из статуса прогона.
        </p>
      </template>

      <!-- 4. Tasks — provisional: active runs -->
      <template v-else-if="facet === 'tasks'">
        <p class="mb-3 text-xs text-base-content/50">
          Черновик: активные прогоны как «сейчас в работе».
        </p>
        <p v-if="activeRuns.length === 0" class="text-base-content/60">
          Актуальных задач сейчас нет.
        </p>
        <ol v-else class="space-y-2">
          <li
            v-for="run in activeRuns"
            :key="run.skillRunId"
            class="rounded-xl border border-base-300 px-3 py-2"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="truncate font-mono text-sm">{{ run.skillId }}</p>
                <p class="mt-0.5 text-xs text-base-content/60">
                  {{ runStatusWord(run.status) }} ·
                  <span class="font-mono">{{ run.currentState }}</span>
                </p>
              </div>
              <SkillRunStatusBadge :status="run.status" />
            </div>
            <div class="mt-2 space-y-2">
              <MemoryRecord title="params" :record="run.params" />
              <MemoryRecord title="vars" :record="run.vars" />
            </div>
          </li>
        </ol>
      </template>

      <!-- 5. Others — interaction manifesto -->
      <template v-else-if="facet === 'others'">
        <p v-if="!memory?.interaction" class="text-base-content/60">
          Манифест взаимодействия ещё не появился.
        </p>
        <template v-else>
          <p class="text-base-content/60">
            Связи: вход по умолчанию
            {{ memory.interaction.defaultAllowInbound ? "разрешён" : "запрещён" }}, выход
            {{ memory.interaction.defaultAllowOutbound ? "разрешён" : "запрещён" }}.
          </p>
          <p v-if="memory.interaction.peers.length === 0" class="mt-3 text-base-content/60">
            Других в манифесте пока нет — адреса канала «Агенты».
          </p>
          <ul v-else class="mt-3 space-y-2">
            <li
              v-for="peer in memory.interaction.peers"
              :key="peer.agentSlug"
              class="rounded-xl border border-base-300 px-3 py-2"
            >
              <p class="font-mono text-sm">{{ peer.name || peer.agentSlug }}</p>
              <p class="mt-0.5 text-xs text-base-content/60">
                /{{ peer.agentSlug }} · вход {{ peer.allowInbound ? "да" : "нет" }} · выход
                {{ peer.allowOutbound ? "да" : "нет" }}
              </p>
            </li>
          </ul>
        </template>
      </template>

      <!-- 6. Skills memory -->
      <template v-else-if="facet === 'skills'">
        <p class="mb-3 text-xs text-base-content/50">
          Черновик: список навыков агента. Куски памяти при установке — следующий слой.
        </p>
        <p v-if="!skillNames?.length" class="text-base-content/60">Навыков у агента пока нет.</p>
        <ul v-else class="space-y-2">
          <li
            v-for="skill in skillNames"
            :key="skill.id"
            class="rounded-xl border border-base-300 px-3 py-2"
          >
            <p class="text-sm font-medium">{{ skill.name }}</p>
            <p class="mt-0.5 font-mono text-xs text-base-content/55">{{ skill.id }}</p>
            <p class="mt-2 rounded-lg border border-dashed border-base-300 px-2 py-1.5 text-xs text-base-content/50">
              Память навыка ещё не установлена
            </p>
          </li>
        </ul>
      </template>

      <!-- 7. Attention zone -->
      <template v-else-if="facet === 'focus'">
        <p class="mb-2 text-base-content/60">
          В фокусе не больше
          <span class="font-semibold text-base-content">{{ MEMORY_ATTENTION_CAPACITY }}</span>
          карточек.
        </p>
        <p v-if="attentionCards.length === 0" class="rounded-xl border border-dashed border-base-300 px-3 py-4 text-base-content/60">
          Зона внимания пуста. Сюда попадут выбранные карточки из полок (другие, задачи…).
        </p>
        <ul v-else class="space-y-2">
          <li
            v-for="card in attentionCards"
            :key="card.id"
            class="rounded-xl border border-base-300 px-3 py-2"
          >
            <p class="text-[10px] uppercase tracking-wide text-base-content/45">{{ card.kind }}</p>
            <p class="font-mono text-sm">{{ card.title }}</p>
          </li>
        </ul>
        <p class="mt-3 text-xs text-base-content/45">
          Занято {{ attentionCards.length }} / {{ MEMORY_ATTENTION_CAPACITY }}
          (черновая автосборка из связей и активных задач).
        </p>
      </template>
    </div>
  </div>
</template>
