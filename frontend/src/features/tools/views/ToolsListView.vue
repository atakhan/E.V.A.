<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useTools } from "@/features/tools/composables/useTools";
import type { ToolDefinition } from "@/features/tools/types/tool";
import { mergeConfigDefaults } from "@/features/tools/utils/instanceConfig";
import {
  instanceStatusBadge,
  instanceTypeName,
} from "@/features/tools/utils/toolInstanceCardMeta";
import { agentToolInstancePath, toolsLibraryPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
}>();

const router = useRouter();
const { catalog, getInstances, addInstance } = useTools();

const libraryOpen = ref(false);
const instances = computed(() => getInstances(props.agentSlug));

function nextInstanceName(type: ToolDefinition): string {
  const n = instances.value.filter((item) => item.toolId === type.id).length + 1;
  return n === 1 ? type.name : `${type.name} ${n}`;
}

function nextInstanceId(type: ToolDefinition): string {
  const n = instances.value.filter((item) => item.toolId === type.id).length + 1;
  return n === 1 ? type.id : `${type.id}_${n}`;
}

function addFromLibrary(type: ToolDefinition) {
  const result = addInstance(props.agentSlug, type.id, {
    id: nextInstanceId(type),
    name: nextInstanceName(type),
    config: mergeConfigDefaults(type.id, {}),
  });
  if (result.ok) {
    libraryOpen.value = false;
    void router.push(agentToolInstancePath(props.agentSlug, result.instance.id));
  }
}

function openInstance(instanceId: string) {
  void router.push(agentToolInstancePath(props.agentSlug, instanceId));
}
</script>

<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Tools</h2>
        <p class="text-sm text-base-content/60">
          Подключения агента — нажмите на карточку для настройки
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <RouterLink :to="toolsLibraryPath()" class="btn btn-ghost btn-sm">
          Глобальная библиотека →
        </RouterLink>
        <button type="button" class="btn btn-sm" @click="libraryOpen = true">
          + Добавить instance
        </button>
      </div>
    </div>

    <div
      v-if="instances.length === 0"
      class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-12 text-center"
    >
      <p class="font-medium">Пока нет tool instances</p>
      <p class="mt-2 text-sm text-base-content/60">
        Добавьте экземпляр из библиотеки — Telegram, Polza, Web Client и др.
      </p>
      <button type="button" class="btn btn-sm mt-4" @click="libraryOpen = true">
        Открыть библиотеку
      </button>
    </div>

    <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <button
        v-for="instance in instances"
        :key="instance.id"
        type="button"
        class="card card-border border-base-300 bg-base-100 text-left shadow-sm transition hover:border-primary/40"
        @click="openInstance(instance.id)"
      >
        <div class="card-body gap-2 p-4">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <h3 class="truncate font-medium">{{ instance.name }}</h3>
              <p class="truncate font-mono text-[10px] text-base-content/50">{{ instance.id }}</p>
            </div>
            <span class="badge badge-xs shrink-0" :class="instanceStatusBadge(instance).class">
              {{ instanceStatusBadge(instance).label }}
            </span>
          </div>
          <p class="text-xs text-base-content/60">{{ instanceTypeName(instance) }}</p>
          <p
            v-if="typeof instance.config.model === 'string' && instance.config.model"
            class="truncate font-mono text-[10px] text-base-content/45"
          >
            model: {{ instance.config.model }}
          </p>
        </div>
      </button>
    </div>

    <dialog class="modal" :class="{ 'modal-open': libraryOpen }">
      <div class="modal-box max-w-2xl">
        <h3 class="text-lg font-semibold">Библиотека Tools</h3>
        <p class="mt-1 text-sm text-base-content/60">
          Выберите тип — будет создан новый instance у этого агента
        </p>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          <button
            v-for="type in catalog"
            :key="type.id"
            type="button"
            class="card card-border border-base-300 bg-base-200/30 text-left transition hover:border-primary hover:bg-base-100"
            @click="addFromLibrary(type)"
          >
            <div class="card-body gap-1 p-4">
              <h4 class="font-medium">{{ type.name }}</h4>
              <p class="line-clamp-2 text-xs text-base-content/60">{{ type.description }}</p>
              <p class="font-mono text-[10px] text-base-content/40">{{ type.id }}</p>
              <p class="text-[10px] text-base-content/45">
                {{ type.commands.length }} cmd ·
                {{ instances.filter((i) => i.toolId === type.id).length }} у агента
              </p>
            </div>
          </button>
        </div>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" @click="libraryOpen = false">Закрыть</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="libraryOpen = false">
        <button type="submit">close</button>
      </form>
    </dialog>
  </section>
</template>
