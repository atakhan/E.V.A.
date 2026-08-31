<script setup lang="ts">
import SkillRunStatusBadge from "@/features/runtime/components/SkillRunStatusBadge.vue";
import type { SkillRunSummary } from "@/features/runtime/types/runtime";

defineProps<{
  items: SkillRunSummary[];
  loading?: boolean;
  refreshing?: boolean;
  showAgent?: boolean;
}>();

const emit = defineEmits<{
  open: [run: SkillRunSummary];
  cancel: [run: SkillRunSummary];
}>();

function formatTime(value: string): string {
  return new Date(value).toLocaleString();
}

function canCancel(status: string): boolean {
  return status === "running" || status === "waiting";
}
</script>

<template>
  <div class="relative overflow-x-auto rounded-2xl border border-base-300 bg-base-100 shadow-sm">
    <span
      v-if="refreshing"
      class="absolute right-3 top-3 z-10 loading loading-spinner loading-xs text-base-content/40"
      aria-label="Обновление"
    />
    <table class="table table-sm">
      <thead>
        <tr class="text-xs uppercase tracking-wide text-base-content/50">
          <th v-if="showAgent">Agent</th>
          <th>Skill</th>
          <th>State</th>
          <th>Status</th>
          <th>Conversation</th>
          <th>Updated</th>
          <th class="text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading && !items.length">
          <td :colspan="showAgent ? 7 : 6" class="text-center text-sm text-base-content/50">
            Загрузка…
          </td>
        </tr>
        <tr v-else-if="!items.length">
          <td :colspan="showAgent ? 7 : 6" class="text-center text-sm text-base-content/50">
            Нет skill runs
          </td>
        </tr>
        <tr
          v-for="run in items"
          v-else
          :key="run.skillRunId"
          class="hover:bg-base-200/40"
        >
          <td v-if="showAgent" class="font-mono text-xs">{{ run.agentSlug }}</td>
          <td class="font-mono text-xs">{{ run.skillId }}</td>
          <td class="font-mono text-xs">{{ run.currentState }}</td>
          <td><SkillRunStatusBadge :status="run.status" /></td>
          <td class="max-w-[12rem] truncate font-mono text-xs text-base-content/70">
            {{ run.conversationId ?? "—" }}
          </td>
          <td class="text-xs text-base-content/60">{{ formatTime(run.updatedAt) }}</td>
          <td class="text-right">
            <div class="flex justify-end gap-1">
              <button type="button" class="btn btn-xs btn-ghost" @click="emit('open', run)">
                Open
              </button>
              <button
                v-if="canCancel(run.status)"
                type="button"
                class="btn btn-xs btn-ghost text-error"
                @click="emit('cancel', run)"
              >
                Cancel
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
