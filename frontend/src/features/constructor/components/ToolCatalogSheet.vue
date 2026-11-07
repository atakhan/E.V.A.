<script setup lang="ts">
import { computed } from "vue";
import { UNIMPLEMENTED_TOOL_LABEL } from "@/features/tools/registry/builtinTools";

const props = defineProps<{
  open: boolean;
  eyebrow: string;
  title: string;
  description: string;
  emptyText: string;
  tools: Array<{ id: string; name: string; description: string; implemented?: boolean }>;
  connectedIds: string[];
}>();

const emit = defineEmits<{
  close: [];
  pick: [toolId: string];
}>();

const items = computed(() =>
  props.tools
    .map((tool) => ({
      ...tool,
      connected: props.connectedIds.includes(tool.id),
      unavailable: tool.implemented === false,
    }))
    .sort((a, b) => Number(a.unavailable) - Number(b.unavailable)),
);
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="translate-y-full"
      enter-to-class="translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="translate-y-0"
      leave-to-class="translate-y-full"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex flex-col bg-base-100"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
      >
        <header class="flex items-start justify-between gap-4 border-b border-base-300 px-6 py-5">
          <div>
            <p class="text-xs uppercase tracking-wide text-base-content/50">{{ eyebrow }}</p>
            <h2 class="mt-1 text-xl font-semibold">{{ title }}</h2>
            <p class="mt-1 max-w-xl text-sm text-base-content/60">{{ description }}</p>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-ghost"
            aria-label="Закрыть"
            @click="emit('close')"
          >
            Закрыть
          </button>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 py-6">
          <ul class="mx-auto grid max-w-3xl gap-3">
            <li v-for="tool in items" :key="tool.id">
              <button
                type="button"
                class="flex w-full flex-col items-start rounded-2xl border px-4 py-4 text-left transition"
                :class="
                  tool.connected || tool.unavailable
                    ? 'cursor-default border-base-300/70 bg-base-200/40 text-base-content/50'
                    : 'border-base-300 bg-base-100 hover:border-primary/50'
                "
                :disabled="tool.connected || tool.unavailable"
                @click="emit('pick', tool.id)"
              >
                <span class="text-base font-semibold">{{ tool.name }}</span>
                <span v-if="tool.description" class="mt-1 text-sm text-base-content/60">
                  {{ tool.description }}
                </span>
                <span v-if="tool.connected" class="mt-2 text-xs uppercase tracking-wide">
                  Уже на столе
                </span>
                <span v-else-if="tool.unavailable" class="mt-2 text-xs uppercase tracking-wide">
                  {{ UNIMPLEMENTED_TOOL_LABEL }}
                </span>
              </button>
            </li>
          </ul>
          <p v-if="tools.length === 0" class="text-center text-sm text-base-content/50">
            {{ emptyText }}
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
