<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import CanvasToolbar from "@/features/modules/fsm/components/CanvasToolbar.vue";
import CanvasFloatingBar from "@/features/modules/fsm/components/CanvasFloatingBar.vue";
import DotCanvas from "@/features/modules/fsm/components/DotCanvas.vue";
import { useFsmCanvases } from "@/features/modules/fsm/composables/useFsmCanvases";
import type { CanvasEditorState, CanvasTool } from "@/features/modules/fsm/types/canvas";
import { applicationModulePath, defaultModuleSlug } from "@/router/paths";

const props = defineProps<{
  appSlug: string;
  canvasId: string;
}>();

const router = useRouter();
const { getCanvas, updateCanvas } = useFsmCanvases();

const activeTool = ref<CanvasTool>("select");
const canvas = computed(() => getCanvas(props.appSlug, props.canvasId));

const editorState = ref<CanvasEditorState>({
  rectangles: [],
  viewport: { panX: 0, panY: 0, zoom: 1 },
});

function loadEditorState() {
  const value = getCanvas(props.appSlug, props.canvasId);
  if (!value) return;
  editorState.value = {
    rectangles: value.rectangles.map((rect) => ({ ...rect })),
    viewport: { ...value.viewport },
  };
}

// Load only when navigating to a canvas — not on every save (avoids feedback loop).
watch(
  () => [props.appSlug, props.canvasId] as const,
  () => loadEditorState(),
  { immediate: true },
);

watch(
  editorState,
  (value) => {
    if (!getCanvas(props.appSlug, props.canvasId)) return;
    updateCanvas(props.appSlug, props.canvasId, {
      rectangles: value.rectangles,
      viewport: value.viewport,
    });
  },
  { deep: true },
);

const canvasTitle = computed(() => canvas.value?.name ?? "Холст");

async function goHome() {
  await router.push(applicationModulePath(props.appSlug, defaultModuleSlug));
}
</script>

<template>
  <div v-if="canvas" class="relative h-screen">
    <DotCanvas
      :key="`${appSlug}:${canvasId}`"
      v-model="editorState"
      :active-tool="activeTool"
    />
    <CanvasFloatingBar :title="canvasTitle" @home="goHome" />
    <CanvasToolbar v-model:active-tool="activeTool" />
  </div>
  <div v-else class="flex h-screen items-center justify-center bg-base-200">
    <p class="text-sm text-base-content/60">Холст не найден</p>
  </div>
</template>
