<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useFsmCanvases } from "@/features/modules/fsm/composables/useFsmCanvases";
import { fsmCanvasPath } from "@/router/paths";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  appSlug: string;
}>();

const router = useRouter();
const { getCanvases, createCanvas, renameCanvas, deleteCanvas } = useFsmCanvases();

const renamingId = ref<string | null>(null);
const renameValue = ref("");

const canvases = computed(() => getCanvases(props.appSlug));

function startRename(canvas: { id: string; name: string }) {
  renamingId.value = canvas.id;
  renameValue.value = canvas.name;
}

function commitRename(id: string) {
  renameCanvas(props.appSlug, id, renameValue.value);
  renamingId.value = null;
}

async function openCanvas(id: string) {
  await router.push(fsmCanvasPath(props.appSlug, id));
}

async function createAndOpenCanvas() {
  const canvas = createCanvas(props.appSlug);
  if (!canvas) return;
  await router.push(fsmCanvasPath(props.appSlug, canvas.id));
}
</script>

<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Холсты FSM</h2>
        <p class="text-sm text-base-content/60">
          Визуальные схемы автоматов и блоков
        </p>
      </div>
      <button type="button" class="btn btn-sm" @click="createAndOpenCanvas()">
        Новый холст
      </button>
    </div>

    <div
      v-if="canvases.length === 0"
      class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-12 text-center"
    >
      <p class="font-medium">Пока нет холстов</p>
      <p class="mt-2 text-sm text-base-content/60">
        Создайте первый холст для проектирования FSM
      </p>
      <button type="button" class="btn btn-sm mt-4" @click="createAndOpenCanvas()">
        Создать холст
      </button>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="canvas in canvases"
        :key="canvas.id"
        class="card border border-base-300 bg-base-100 shadow-sm transition hover:shadow-md"
      >
        <div class="card-body gap-4">
          <button
            type="button"
            class="aspect-video w-full rounded-xl border border-base-300 bg-base-200/70 transition hover:border-primary/40"
            @click="openCanvas(canvas.id)"
          >
            <div class="flex h-full items-center justify-center text-xs text-base-content/50">
              {{ canvas.rectangles.length }} блоков
            </div>
          </button>

          <div class="space-y-2">
            <div v-if="renamingId === canvas.id" class="join w-full">
              <input
                v-model="renameValue"
                class="input input-sm join-item w-full"
                @keydown.enter="commitRename(canvas.id)"
                @keydown.escape="renamingId = null"
              />
              <button type="button" class="btn btn-sm join-item" @click="commitRename(canvas.id)">
                OK
              </button>
            </div>
            <button
              v-else
              type="button"
              class="text-left text-base font-medium hover:text-primary"
              @click="openCanvas(canvas.id)"
            >
              {{ canvas.name }}
            </button>

            <p class="text-xs text-base-content/50">
              Обновлено {{ formatDateTime(canvas.updatedAt) }}
            </p>
          </div>

          <div class="card-actions justify-end">
            <button type="button" class="btn btn-xs btn-ghost" @click="startRename(canvas)">
              Переименовать
            </button>
            <button type="button" class="btn btn-xs btn-ghost text-error" @click="deleteCanvas(appSlug, canvas.id)">
              Удалить
            </button>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
