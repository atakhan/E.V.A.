<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";
import {
  clamp,
  isValidRect,
  normalizeRect,
  screenToWorld,
  snap,
  snapPoint,
  snapRect,
} from "@/features/modules/fsm/utils/canvasGeometry";
import {
  GRID_SIZE,
  type CanvasRect,
  type CanvasTool,
  type CanvasEditorState,
  type DraftRect,
  type Point,
} from "@/features/modules/fsm/types/canvas";
import { createId } from "@/shared/utils/id";

const props = defineProps<{
  activeTool: CanvasTool;
}>();

const model = defineModel<CanvasEditorState>({ required: true });

const viewportEl = useTemplateRef<HTMLElement>("viewport");

const panX = ref(model.value.viewport.panX);
const panY = ref(model.value.viewport.panY);
const zoom = ref(model.value.viewport.zoom);

const rectangles = ref<CanvasRect[]>([...model.value.rectangles]);
const selectedId = ref<string | null>(null);
const draftRect = ref<DraftRect | null>(null);

type Interaction =
  | { kind: "pan"; startClient: Point; startPan: Point }
  | { kind: "draw"; anchor: Point }
  | { kind: "move"; id: string; offset: Point };

const interaction = ref<Interaction | null>(null);

function syncModel() {
  model.value = {
    rectangles: rectangles.value.map((rect) => ({ ...rect })),
    viewport: {
      panX: panX.value,
      panY: panY.value,
      zoom: zoom.value,
    },
  };
}

watch([rectangles, panX, panY, zoom], syncModel, { deep: true });

const viewportClass = computed(() =>
  props.activeTool === "rectangle" ? "canvas-viewport--draw" : "canvas-viewport--select",
);

const worldStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
  transformOrigin: "0 0",
}));

const gridStyle = computed(() => ({
  backgroundSize: `${GRID_SIZE}px ${GRID_SIZE}px`,
}));

function getViewportRect(): DOMRect {
  return viewportEl.value!.getBoundingClientRect();
}

function toWorld(clientX: number, clientY: number): Point {
  return screenToWorld(
    clientX,
    clientY,
    getViewportRect(),
    panX.value,
    panY.value,
    zoom.value,
  );
}

function toSnappedWorld(clientX: number, clientY: number): Point {
  return snapPoint(toWorld(clientX, clientY));
}

function findRectAt(point: Point): CanvasRect | undefined {
  for (let i = rectangles.value.length - 1; i >= 0; i -= 1) {
    const rect = rectangles.value[i];
    if (
      point.x >= rect.x &&
      point.x <= rect.x + rect.width &&
      point.y >= rect.y &&
      point.y <= rect.y + rect.height
    ) {
      return rect;
    }
  }
  return undefined;
}

function onWheel(event: WheelEvent) {
  event.preventDefault();

  const rect = getViewportRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  const factor = event.deltaY > 0 ? 0.9 : 1.1;
  const nextZoom = clamp(zoom.value * factor, 0.25, 2.5);

  const worldX = (mouseX - panX.value) / zoom.value;
  const worldY = (mouseY - panY.value) / zoom.value;

  zoom.value = nextZoom;
  panX.value = mouseX - worldX * nextZoom;
  panY.value = mouseY - worldY * nextZoom;
}

function onPointerDown(event: PointerEvent) {
  if (event.button === 1) {
    event.preventDefault();
    interaction.value = {
      kind: "pan",
      startClient: { x: event.clientX, y: event.clientY },
      startPan: { x: panX.value, y: panY.value },
    };
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  if (event.button !== 0) return;

  const worldPoint = toSnappedWorld(event.clientX, event.clientY);
  const hit = findRectAt(worldPoint);

  if (props.activeTool === "rectangle") {
    if (hit) {
      selectedId.value = hit.id;
      interaction.value = {
        kind: "move",
        id: hit.id,
        offset: { x: worldPoint.x - hit.x, y: worldPoint.y - hit.y },
      };
    } else {
      selectedId.value = null;
      interaction.value = { kind: "draw", anchor: worldPoint };
      draftRect.value = {
        x: worldPoint.x,
        y: worldPoint.y,
        width: GRID_SIZE,
        height: GRID_SIZE,
      };
    }
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  if (hit) {
    selectedId.value = hit.id;
    interaction.value = {
      kind: "move",
      id: hit.id,
      offset: { x: worldPoint.x - hit.x, y: worldPoint.y - hit.y },
    };
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  selectedId.value = null;
  interaction.value = {
    kind: "pan",
    startClient: { x: event.clientX, y: event.clientY },
    startPan: { x: panX.value, y: panY.value },
  };
  viewportEl.value?.setPointerCapture(event.pointerId);
}

function onPointerMove(event: PointerEvent) {
  const current = interaction.value;
  if (!current) return;

  if (current.kind === "pan") {
    panX.value = current.startPan.x + (event.clientX - current.startClient.x);
    panY.value = current.startPan.y + (event.clientY - current.startClient.y);
    return;
  }

  if (current.kind === "draw") {
    const end = toSnappedWorld(event.clientX, event.clientY);
    draftRect.value = snapRect(normalizeRect(current.anchor, end));
    return;
  }

  const rect = rectangles.value.find((item) => item.id === current.id);
  if (!rect) return;

  const worldPoint = toSnappedWorld(event.clientX, event.clientY);
  rect.x = snap(worldPoint.x - current.offset.x);
  rect.y = snap(worldPoint.y - current.offset.y);
}

function onPointerUp(event: PointerEvent) {
  const current = interaction.value;
  if (!current) return;

  if (current.kind === "draw" && draftRect.value && isValidRect(draftRect.value)) {
    rectangles.value.push({
      id: createId(),
      ...draftRect.value,
    });
    selectedId.value = rectangles.value.at(-1)?.id ?? null;
  }

  draftRect.value = null;
  interaction.value = null;
  viewportEl.value?.releasePointerCapture(event.pointerId);
}

function onKeyDown(event: KeyboardEvent) {
  if (event.key !== "Delete" && event.key !== "Backspace") return;
  if (!selectedId.value) return;

  rectangles.value = rectangles.value.filter((rect) => rect.id !== selectedId.value);
  selectedId.value = null;
}

onMounted(() => {
  window.addEventListener("keydown", onKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
  <div
    ref="viewport"
    class="canvas-viewport relative h-full w-full overflow-hidden bg-base-300"
    :class="viewportClass"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @contextmenu.prevent
  >
    <div class="canvas-world absolute inset-0" :style="worldStyle">
      <div class="canvas-grid absolute inset-0" :style="gridStyle" />

      <div
        v-for="rect in rectangles"
        :key="rect.id"
        class="canvas-rect"
        :class="{ 'canvas-rect--selected': rect.id === selectedId }"
        :style="{
          left: `${rect.x}px`,
          top: `${rect.y}px`,
          width: `${rect.width}px`,
          height: `${rect.height}px`,
        }"
      />

      <div
        v-if="draftRect"
        class="canvas-rect canvas-rect--draft"
        :style="{
          left: `${draftRect.x}px`,
          top: `${draftRect.y}px`,
          width: `${draftRect.width}px`,
          height: `${draftRect.height}px`,
        }"
      />
    </div>

    <div class="pointer-events-none absolute bottom-3 right-3 rounded-box bg-base-100/90 px-3 py-1 text-xs shadow">
      {{ Math.round(zoom * 100) }}% · сетка {{ GRID_SIZE }}px
    </div>
  </div>
</template>

<style scoped>
.canvas-viewport {
  touch-action: none;
  user-select: none;
}

.canvas-viewport--select {
  cursor: grab;
}

.canvas-viewport--select:active {
  cursor: grabbing;
}

.canvas-viewport--draw {
  cursor: crosshair;
}

.canvas-grid {
  background-image: radial-gradient(circle, color-mix(in oklab, var(--color-base-content) 22%, transparent) 1px, transparent 1px);
}

.canvas-rect {
  position: absolute;
  border: 2px solid color-mix(in oklab, var(--color-base-content) 18%, transparent);
  border-radius: 0.75rem;
  background: var(--color-base-100);
  box-shadow:
    0 1px 2px color-mix(in oklab, var(--color-base-content) 10%, transparent),
    0 8px 24px color-mix(in oklab, var(--color-base-content) 6%, transparent);
}

.canvas-rect--selected {
  border-color: var(--color-primary);
  box-shadow:
    0 0 0 2px color-mix(in oklab, var(--color-primary) 25%, transparent),
    0 8px 24px color-mix(in oklab, var(--color-primary) 12%, transparent);
}

.canvas-rect--draft {
  border-style: dashed;
  opacity: 0.85;
  pointer-events: none;
}
</style>
