<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import SkillRunActions from "@/features/runtime/components/SkillRunActions.vue";
import SkillRunStatusBadge from "@/features/runtime/components/SkillRunStatusBadge.vue";
import SkillRunTimeline from "@/features/runtime/components/SkillRunTimeline.vue";
import { useSkillRunDetail } from "@/features/runtime/composables/useSkillRunDetail";
import ToolLogFeed from "@/features/tools/components/ToolLogFeed.vue";
import { agentRuntimePath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  runId: string;
}>();

const router = useRouter();
const { getAgentBySlug } = useAgents();
const agent = computed(() => getAgentBySlug(props.agentSlug));

const runIdRef = computed(() => props.runId);
const { run, history, loading, refreshing, cancelling, error, isTerminal, cancel } = useSkillRunDetail(runIdRef);

async function goBack() {
  await router.push(agentRuntimePath(props.agentSlug));
}

async function handleCancel() {
  const ok = await cancel();
  if (ok) await router.push(agentRuntimePath(props.agentSlug));
}
</script>

<template>
  <section v-if="agent" class="space-y-6">
    <button type="button" class="btn btn-xs btn-ghost -ml-2" @click="goBack()">
      ← Runtime
    </button>

    <p v-if="error" class="rounded-xl border border-error/40 bg-error/5 px-4 py-3 text-sm text-error">
      {{ error }}
    </p>

    <div v-if="loading && !run" class="text-sm text-base-content/50">Загрузка run…</div>

    <template v-else-if="run">
      <div class="relative rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
        <span
          v-if="refreshing"
          class="absolute right-3 top-3 loading loading-spinner loading-xs text-base-content/40"
          aria-label="Обновление"
        />
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold font-mono">{{ run.skillId }}</h2>
            <p class="mt-1 font-mono text-xs text-base-content/50">{{ run.skillRunId }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <SkillRunStatusBadge :status="run.status" />
            <span class="badge badge-outline font-mono">{{ run.currentState }}</span>
          </div>
        </div>

        <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt class="text-base-content/50">Publication</dt>
            <dd class="font-mono">v{{ run.publicationVersion ?? "?" }}</dd>
          </div>
          <div>
            <dt class="text-base-content/50">Conversation</dt>
            <dd class="font-mono">{{ run.conversationId ?? "—" }}</dd>
          </div>
          <div>
            <dt class="text-base-content/50">Created</dt>
            <dd>{{ run.createdAt ? new Date(run.createdAt).toLocaleString() : "—" }}</dd>
          </div>
          <div>
            <dt class="text-base-content/50">Updated</dt>
            <dd>{{ run.updatedAt ? new Date(run.updatedAt).toLocaleString() : "—" }}</dd>
          </div>
        </dl>

        <div v-if="run.error" class="mt-4 rounded-xl border border-error/30 bg-error/5 px-4 py-3 text-sm text-error">
          {{ run.error }}
        </div>

        <div class="mt-4">
          <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">FSM path</p>
          <div class="mt-2 flex flex-wrap gap-1">
            <span
              v-for="(state, index) in run.history"
              :key="`${state}-${index}`"
              class="badge badge-sm font-mono"
              :class="index === run.history.length - 1 ? 'badge-primary' : 'badge-ghost'"
            >
              {{ state }}
            </span>
          </div>
        </div>

        <div class="mt-5">
          <SkillRunActions
            :agent-slug="agentSlug"
            :run="run"
            :is-terminal="isTerminal"
            :cancelling="cancelling"
            @cancel="handleCancel"
          />
        </div>
      </div>

      <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
        <h3 class="font-semibold">Timeline</h3>
        <div class="mt-4">
          <SkillRunTimeline :history="history" />
        </div>
      </div>

      <div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
        <h3 class="font-semibold">Tool logs</h3>
        <div class="mt-4">
          <ToolLogFeed
            :agent-slug="agentSlug"
            :skill-run-id="run.skillRunId"
            :limit="20"
            compact
            :show-header="false"
            :auto-refresh-ms="5000"
            auto-refresh-default
          />
        </div>
      </div>
    </template>
  </section>
</template>
