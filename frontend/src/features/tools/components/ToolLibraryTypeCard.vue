<script setup lang="ts">
import type { ToolLibraryTypeEntry, ToolLibraryUsageRow } from "@/features/tools/utils/buildToolLibraryIndex";
import { instanceStatusBadge } from "@/features/tools/utils/toolInstanceCardMeta";

defineProps<{
  entry: ToolLibraryTypeEntry;
}>();

const emit = defineEmits<{
  openAgent: [slug: string];
  openInstance: [row: ToolLibraryUsageRow];
}>();
</script>

<template>
  <article class="card border border-base-300 bg-base-100 shadow-sm">
    <div class="card-body gap-3">
      <div>
        <h2 class="text-lg font-semibold leading-tight">{{ entry.definition.name }}</h2>
        <p class="mt-1 font-mono text-xs text-base-content/50">{{ entry.definition.id }}</p>
      </div>

      <p
        v-if="entry.definition.description"
        class="line-clamp-3 text-sm text-base-content/60"
      >
        {{ entry.definition.description }}
      </p>
      <p v-else class="text-sm text-base-content/40">Без описания</p>

      <div class="flex flex-wrap gap-1.5">
        <span class="badge badge-sm badge-ghost">
          {{ entry.definition.commands.length }} cmd
        </span>
        <span v-if="entry.definition.events.length" class="badge badge-sm badge-ghost">
          {{ entry.definition.events.length }} events
        </span>
        <span
          class="badge badge-sm"
          :class="entry.instances.length ? 'badge-primary badge-outline' : 'badge-ghost'"
        >
          {{ entry.instances.length }} инстансов
        </span>
        <span v-if="entry.agentCount" class="badge badge-sm badge-ghost">
          {{ entry.agentCount }} агентов
        </span>
        <span v-if="entry.definition.credentialKind" class="badge badge-sm badge-ghost font-mono text-[10px]">
          cred: {{ entry.definition.credentialKind }}
        </span>
      </div>

      <div v-if="entry.instances.length === 0" class="rounded-xl border border-dashed border-base-300 px-4 py-5 text-center text-sm text-base-content/50">
        Не используется
      </div>

      <ul v-else class="space-y-2">
        <li
          v-for="row in entry.instances"
          :key="`${row.agentSlug}:${row.instance.id}`"
          class="rounded-xl border border-base-300 bg-base-200/40 px-3 py-2"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <button
                type="button"
                class="truncate text-left text-sm font-medium hover:text-primary"
                @click="emit('openAgent', row.agentSlug)"
              >
                {{ row.agentName }}
              </button>
              <p class="font-mono text-[10px] text-base-content/45">{{ row.agentSlug }}</p>
              <p class="mt-1 truncate text-xs text-base-content/70">{{ row.instance.name }}</p>
            </div>
            <span
              class="badge badge-xs shrink-0"
              :class="instanceStatusBadge(row.instance).class"
            >
              {{ instanceStatusBadge(row.instance).label }}
            </span>
          </div>
          <div class="mt-2 flex justify-end">
            <button
              type="button"
              class="btn btn-xs btn-ghost"
              @click="emit('openInstance', row)"
            >
              Открыть
            </button>
          </div>
        </li>
      </ul>
    </div>
  </article>
</template>
