<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import {
  filterToolLibraryIndex,
  useToolLibrary,
} from "@/features/tools/composables/useToolLibrary";
import type { ToolLibraryUsageRow } from "@/features/tools/utils/buildToolLibraryIndex";
import { instanceStatusBadge } from "@/features/tools/utils/toolInstanceCardMeta";
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
  <main class="min-h-screen bg-base-200 px-6 py-10">
    <div class="mx-auto max-w-5xl space-y-6">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <button type="button" class="btn btn-xs btn-ghost -ml-2 mb-2" @click="goToAgents()">
            ← Агенты
          </button>
          <h1 class="text-2xl font-semibold tracking-wide">Библиотека Tools</h1>
          <p class="mt-1 text-sm text-base-content/60">
            Каталог типов и использование инстансов по всем агентам
          </p>
          <p class="mt-2 text-sm text-base-content/50">{{ summaryLine }}</p>
        </div>
      </header>

      <div
        v-if="agentCount === 0"
        class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-16 text-center"
      >
        <p class="text-lg font-medium">Пока нет агентов</p>
        <p class="mt-2 text-sm text-base-content/60">
          Создайте агента, чтобы подключать tool instances
        </p>
        <button type="button" class="btn mt-6" @click="goToAgents()">
          Перейти к агентам
        </button>
      </div>

      <template v-else>
        <label class="input input-bordered flex w-full items-center gap-2 bg-base-100">
          <span class="text-base-content/40">⌕</span>
          <input
            v-model="searchQuery"
            type="search"
            class="grow"
            placeholder="Поиск по типу, агенту или instance id…"
          />
        </label>

        <div v-if="filteredIndex.types.length === 0 && filteredIndex.orphanInstances.length === 0" class="rounded-2xl border border-base-300 bg-base-100 px-6 py-12 text-center">
          <p class="font-medium">Ничего не найдено</p>
          <p class="mt-2 text-sm text-base-content/60">Попробуйте другой запрос</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="entry in filteredIndex.types"
            :key="entry.definition.id"
            class="collapse collapse-arrow rounded-2xl border border-base-300 bg-base-100"
          >
            <input type="checkbox" />
            <div class="collapse-title flex flex-wrap items-center gap-2 pr-12 font-medium">
              <span>{{ entry.definition.name }}</span>
              <span class="font-mono text-xs font-normal text-base-content/45">
                {{ entry.definition.id }}
              </span>
              <span class="badge badge-sm badge-ghost">
                {{ entry.instances.length }} инстансов · {{ entry.agentCount }} агентов
              </span>
            </div>
            <div class="collapse-content space-y-3 text-sm">
              <p class="text-base-content/60">{{ entry.definition.description }}</p>
              <p class="text-xs text-base-content/45">
                {{ entry.definition.commands.length }} cmd
                <span v-if="entry.enabledCount > 0"> · {{ entry.enabledCount }} включено</span>
              </p>

              <p
                v-if="entry.instances.length === 0"
                class="rounded-xl border border-dashed border-base-300 px-4 py-6 text-center text-base-content/50"
              >
                Не используется
              </p>

              <div v-else class="overflow-x-auto rounded-xl border border-base-300">
                <table class="table table-sm">
                  <thead>
                    <tr class="text-base-content/60">
                      <th>Агент</th>
                      <th>Instance</th>
                      <th>Статус</th>
                      <th class="text-right">Действие</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in entry.instances" :key="`${row.agentSlug}:${row.instance.id}`">
                      <td>
                        <button
                          type="button"
                          class="link link-hover text-left"
                          @click="openAgentTools(row.agentSlug)"
                        >
                          {{ row.agentName }}
                        </button>
                        <p class="font-mono text-[10px] text-base-content/40">{{ row.agentSlug }}</p>
                      </td>
                      <td>
                        <p>{{ row.instance.name }}</p>
                        <p class="font-mono text-[10px] text-base-content/40">{{ row.instance.id }}</p>
                      </td>
                      <td>
                        <span
                          class="badge badge-xs"
                          :class="instanceStatusBadge(row.instance).class"
                        >
                          {{ instanceStatusBadge(row.instance).label }}
                        </span>
                      </td>
                      <td class="text-right">
                        <button
                          type="button"
                          class="btn btn-xs btn-ghost"
                          @click="openInstance(row)"
                        >
                          Открыть
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <section
            v-if="filteredIndex.orphanInstances.length > 0"
            class="rounded-2xl border border-warning/40 bg-base-100 p-4"
          >
            <h2 class="font-medium text-warning">Неизвестные типы</h2>
            <p class="mt-1 text-sm text-base-content/60">
              Инстансы с toolId, которого нет в каталоге
            </p>
            <div class="mt-3 overflow-x-auto rounded-xl border border-base-300">
              <table class="table table-sm">
                <thead>
                  <tr class="text-base-content/60">
                    <th>Агент</th>
                    <th>Instance</th>
                    <th>toolId</th>
                    <th class="text-right">Действие</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in filteredIndex.orphanInstances"
                    :key="`${row.agentSlug}:${row.instance.id}`"
                  >
                    <td>{{ row.agentName }}</td>
                    <td>
                      <p>{{ row.instance.name }}</p>
                      <p class="font-mono text-[10px] text-base-content/40">{{ row.instance.id }}</p>
                    </td>
                    <td class="font-mono text-xs">{{ row.instance.toolId }}</td>
                    <td class="text-right">
                      <button
                        type="button"
                        class="btn btn-xs btn-ghost"
                        @click="openInstance(row)"
                      >
                        Открыть
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </template>
    </div>
  </main>
</template>
