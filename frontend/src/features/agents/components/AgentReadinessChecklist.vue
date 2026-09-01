<script setup lang="ts">
import { useRouter } from "vue-router";
import type { AgentReadinessItem } from "@/features/agents/composables/useAgentOverview";

defineProps<{
  items: AgentReadinessItem[];
  progress: number;
}>();

const router = useRouter();
</script>

<template>
  <section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="font-semibold">Готовность к запуску</h3>
        <p class="mt-1 text-sm text-base-content/60">
          Шаги конструктора перед публикацией и runtime
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-sm text-base-content/60">{{ progress }}%</span>
        <progress
          class="progress progress-primary w-24"
          :value="progress"
          max="100"
          :aria-label="`Готовность ${progress}%`"
        />
      </div>
    </div>

    <ul class="mt-4 space-y-2">
      <li v-for="item in items" :key="item.id">
        <button
          type="button"
          class="flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition"
          :class="
            item.done
              ? 'border-success/30 bg-success/5 hover:border-success/50'
              : 'border-base-300 bg-base-200/20 hover:border-primary/40'
          "
          @click="router.push(item.href)"
        >
          <span
            class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
            :class="
              item.done
                ? 'bg-success text-success-content'
                : item.optional
                  ? 'border border-dashed border-base-content/30 text-base-content/40'
                  : 'border border-base-content/20 text-base-content/40'
            "
            aria-hidden="true"
          >
            {{ item.done ? "✓" : item.optional ? "·" : "" }}
          </span>

          <span class="min-w-0 flex-1">
            <span class="flex flex-wrap items-center gap-2">
              <span class="font-medium">{{ item.label }}</span>
              <span v-if="item.optional" class="badge badge-ghost badge-xs">опционально</span>
            </span>
            <span class="mt-0.5 block text-sm text-base-content/60">{{ item.description }}</span>
          </span>

          <span class="shrink-0 text-xs text-base-content/40">→</span>
        </button>
      </li>
    </ul>
  </section>
</template>
