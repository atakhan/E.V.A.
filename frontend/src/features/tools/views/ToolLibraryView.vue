<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import ToolLibraryOrphanCard from "@/features/tools/components/ToolLibraryOrphanCard.vue";
import ToolLibraryTypeCard from "@/features/tools/components/ToolLibraryTypeCard.vue";
import {
  filterToolLibraryIndex,
  useToolLibrary,
} from "@/features/tools/composables/useToolLibrary";
import type { ToolLibraryUsageRow } from "@/features/tools/utils/buildToolLibraryIndex";
import {
  agentToolInstancePath,
  agentToolsPath,
  agentsPath,
} from "@/router/paths";

const router = useRouter();
const { catalog, index, agentCount, uniqueAgentSlugsWithInstances } = useToolLibrary();

const searchQuery = ref("");

const filteredIndex = computed(() => filterToolLibraryIndex(index.value, searchQuery.value));

const summaryLine = computed(() => {
  const typeCount = catalog.length;
  const instanceCount = index.value.totalInstances;
  const agentsWithTools = uniqueAgentSlugsWithInstances.value;
  return `${typeCount} типов · ${instanceCount} инстансов в ${agentsWithTools} агентах`;
});

const hasResults = computed(
  () => filteredIndex.value.types.length > 0 || filteredIndex.value.orphanInstances.length > 0,
);

async function goToAgents() {
  await router.push(agentsPath());
}

async function openAgentTools(agentSlug: string) {
  await router.push(agentToolsPath(agentSlug));
}

async function openInstance(row: ToolLibraryUsageRow) {
  await router.push(agentToolInstancePath(row.agentSlug, row.instance.id));
}
</script>

<template>
  <div class="px-6 py-8 lg:px-8">
    <div class="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 class="text-2xl font-semibold tracking-wide">Библиотека Tools</h1>
        <p class="mt-1 text-sm text-base-content/60">
          Справочник типов tools и их использование в агентах
        </p>
        <p class="mt-2 text-sm text-base-content/50">{{ summaryLine }}</p>
      </header>

      <div
        v-if="agentCount === 0"
        class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-4 text-sm text-base-content/60"
      >
        Агентов пока нет — каталог типов доступен ниже. Чтобы подключить instance, создайте агента.
        <button type="button" class="btn btn-xs btn-ghost ml-2" @click="goToAgents()">
          К агентам
        </button>
      </div>

      <label class="input input-bordered flex w-full items-center gap-2 bg-base-100">
        <span class="text-base-content/40">⌕</span>
        <input
          v-model="searchQuery"
          type="search"
          class="grow"
          placeholder="Поиск по типу, агенту или instance id…"
        />
      </label>

      <div
        v-if="!hasResults"
        class="rounded-2xl border border-base-300 bg-base-100 px-6 py-12 text-center"
      >
        <p class="font-medium">Ничего не найдено</p>
        <p class="mt-2 text-sm text-base-content/60">Попробуйте другой запрос</p>
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <ToolLibraryTypeCard
          v-for="entry in filteredIndex.types"
          :key="entry.definition.id"
          :entry="entry"
          @open-agent="openAgentTools"
          @open-instance="openInstance"
        />
      </div>

      <section v-if="filteredIndex.orphanInstances.length > 0" class="space-y-3">
        <div>
          <h2 class="text-lg font-semibold text-warning">Неизвестные типы</h2>
          <p class="mt-1 text-sm text-base-content/60">
            Инстансы с toolId, которого нет в каталоге
          </p>
        </div>
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <ToolLibraryOrphanCard
            v-for="row in filteredIndex.orphanInstances"
            :key="`${row.agentSlug}:${row.instance.id}`"
            :row="row"
            @open-instance="openInstance(row)"
          />
        </div>
      </section>
    </div>
  </div>
</template>
