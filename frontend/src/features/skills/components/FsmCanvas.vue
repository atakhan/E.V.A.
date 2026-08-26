<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";
import {
  borderPointToward,
  clamp,
  isValidRect,
  normalizeRect,
  screenToWorld,
  snap,
  snapPoint,
  snapRect,
  stateCenter,
} from "@/features/skills/utils/canvasGeometry";
import {
  GRID_SIZE,
  type CanvasTool,
  type DraftRect,
  type FsmEditorState,
  type FsmSelection,
  type FsmState,
  type Point,
} from "@/features/skills/types/fsm";
import { createFsmState, createFsmTransition } from "@/features/skills/types/skill";

const props = defineProps<{
  activeTool: CanvasTool;
}>();

const model = defineModel<FsmEditorState>({ required: true });
const selection = defineModel<FsmSelection>("selection", { default: null });

const viewportEl = useTemplateRef<HTMLElement>("viewport");

const draftRect = ref<DraftRect | null>(null);
const transitionFromId = ref<string | null>(null);
const draftLinkTo = ref<Point | null>(null);

type Interaction =
  | { kind: "pan"; startClient: Point; startPan: Point }
  | { kind: "draw"; anchor: Point }
  | { kind: "move"; id: string; offset: Point };

const interaction = ref<Interaction | null>(null);

watch(
  () => props.activeTool,
  () => {
    transitionFromId.value = null;
    draftLinkTo.value = null;
  },
);

const states = computed(() => model.value.states);
const initial = computed(() => model.value.initial);

const draftLinkStart = computed(() => {
  if (!transitionFromId.value) return null;
  const state = states.value.find((item) => item.id === transitionFromId.value);
  return state ? stateCenter(state) : null;
});

const viewportClass = computed(() => {
  if (props.activeTool === "state") return "canvas-viewport--draw";
  if (props.activeTool === "transition") return "canvas-viewport--link";
  return "canvas-viewport--select";
});

const worldStyle = computed(() => ({
  transform: `translate(${model.value.viewport.panX}px, ${model.value.viewport.panY}px) scale(${model.value.viewport.zoom})`,
  transformOrigin: "0 0",
}));

const gridStyle = computed(() => ({
  backgroundSize: `${GRID_SIZE}px ${GRID_SIZE}px`,
}));

const edges = computed(() => {
  const byId = new Map(states.value.map((state) => [state.id, state]));
  const result: Array<{
    key: string;
    stateId: string;
    transitionId: string;
    event: string;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    mx: number;
    my: number;
    selected: boolean;
  }> = [];

  for (const state of states.value) {
    for (const transition of state.transitions) {
      const target = byId.get(transition.to);
      if (!target) continue;
      const start = borderPointToward(state, stateCenter(target));
      const end = borderPointToward(target, stateCenter(state));
      const selected =
        selection.value?.kind === "transition" &&
        selection.value.stateId === state.id &&
        selection.value.transitionId === transition.id;
      result.push({
        key: `${state.id}:${transition.id}`,
        stateId: state.id,
        transitionId: transition.id,
        event: transition.event,
        x1: start.x,
        y1: start.y,
        x2: end.x,
        y2: end.y,
        mx: (start.x + end.x) / 2,
        my: (start.y + end.y) / 2,
        selected,
      });
    }
  }
  return result;
});

function getViewportRect(): DOMRect {
  return viewportEl.value!.getBoundingClientRect();
}

function toWorld(clientX: number, clientY: number): Point {
  return screenToWorld(
    clientX,
    clientY,
    getViewportRect(),
    model.value.viewport.panX,
    model.value.viewport.panY,
    model.value.viewport.zoom,
  );
}

function toSnappedWorld(clientX: number, clientY: number): Point {
  return snapPoint(toWorld(clientX, clientY));
}

function findStateAt(point: Point): FsmState | undefined {
  for (let i = states.value.length - 1; i >= 0; i -= 1) {
    const state = states.value[i];
    if (
      point.x >= state.x &&
      point.x <= state.x + state.width &&
      point.y >= state.y &&
      point.y <= state.y + state.height
    ) {
      return state;
    }
  }
  return undefined;
}

function findEdgeAt(point: Point): { stateId: string; transitionId: string } | null {
  const threshold = 10 / model.value.viewport.zoom;
  for (const edge of edges.value) {
    const dist = distanceToSegment(point, { x: edge.x1, y: edge.y1 }, { x: edge.x2, y: edge.y2 });
    if (dist <= threshold) {
      return { stateId: edge.stateId, transitionId: edge.transitionId };
    }
  }
  return null;
}

function distanceToSegment(point: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  if (dx === 0 && dy === 0) {
    return Math.hypot(point.x - a.x, point.y - a.y);
  }
  const t = Math.max(
    0,
    Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)),
  );
  return Math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy));
}

function onWheel(event: WheelEvent) {
  event.preventDefault();

  const rect = getViewportRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  const factor = event.deltaY > 0 ? 0.9 : 1.1;
  const zoom = model.value.viewport.zoom;
  const nextZoom = clamp(zoom * factor, 0.25, 2.5);

  const worldX = (mouseX - model.value.viewport.panX) / zoom;
  const worldY = (mouseY - model.value.viewport.panY) / zoom;

  model.value.viewport.zoom = nextZoom;
  model.value.viewport.panX = mouseX - worldX * nextZoom;
  model.value.viewport.panY = mouseY - worldY * nextZoom;
}

function onPointerDown(event: PointerEvent) {
  if (event.button === 1) {
    event.preventDefault();
    interaction.value = {
      kind: "pan",
      startClient: { x: event.clientX, y: event.clientY },
      startPan: { x: model.value.viewport.panX, y: model.value.viewport.panY },
    };
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  if (event.button !== 0) return;

  const worldPoint = toSnappedWorld(event.clientX, event.clientY);
  const hit = findStateAt(worldPoint);

  if (props.activeTool === "transition") {
    if (hit) {
      if (!transitionFromId.value) {
        transitionFromId.value = hit.id;
        selection.value = { kind: "state", stateId: hit.id };
        draftLinkTo.value = worldPoint;
      } else if (transitionFromId.value !== hit.id) {
        const source = model.value.states.find((state) => state.id === transitionFromId.value);
        if (source) {
          const transition = createFsmTransition(hit.id);
          source.transitions.push(transition);
          selection.value = {
            kind: "transition",
            stateId: source.id,
            transitionId: transition.id,
          };
        }
        transitionFromId.value = null;
        draftLinkTo.value = null;
      }
    } else {
      transitionFromId.value = null;
      draftLinkTo.value = null;
      selection.value = null;
    }
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  if (props.activeTool === "state") {
    if (hit) {
      selection.value = { kind: "state", stateId: hit.id };
      interaction.value = {
        kind: "move",
        id: hit.id,
        offset: { x: worldPoint.x - hit.x, y: worldPoint.y - hit.y },
      };
    } else {
      selection.value = null;
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

  const edgeHit = findEdgeAt(toWorld(event.clientX, event.clientY));
  if (edgeHit) {
    selection.value = {
      kind: "transition",
      stateId: edgeHit.stateId,
      transitionId: edgeHit.transitionId,
    };
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  if (hit) {
    selection.value = { kind: "state", stateId: hit.id };
    interaction.value = {
      kind: "move",
      id: hit.id,
      offset: { x: worldPoint.x - hit.x, y: worldPoint.y - hit.y },
    };
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  selection.value = null;
  interaction.value = {
    kind: "pan",
    startClient: { x: event.clientX, y: event.clientY },
    startPan: { x: model.value.viewport.panX, y: model.value.viewport.panY },
  };
  viewportEl.value?.setPointerCapture(event.pointerId);
}

function onPointerMove(event: PointerEvent) {
  if (props.activeTool === "transition" && transitionFromId.value) {
    draftLinkTo.value = toWorld(event.clientX, event.clientY);
  }

  const current = interaction.value;
  if (!current) return;

  if (current.kind === "pan") {
    model.value.viewport.panX = current.startPan.x + (event.clientX - current.startClient.x);
    model.value.viewport.panY = current.startPan.y + (event.clientY - current.startClient.y);
    return;
  }

  if (current.kind === "draw") {
    const end = toSnappedWorld(event.clientX, event.clientY);
    draftRect.value = snapRect(normalizeRect(current.anchor, end));
    return;
  }

  const state = model.value.states.find((item) => item.id === current.id);
  if (!state) return;

  const worldPoint = toSnappedWorld(event.clientX, event.clientY);
  state.x = snap(worldPoint.x - current.offset.x);
  state.y = snap(worldPoint.y - current.offset.y);
}

function onPointerUp(event: PointerEvent) {
  const current = interaction.value;

  if (current?.kind === "draw" && draftRect.value && isValidRect(draftRect.value)) {
    const state = createFsmState(model.value.states, draftRect.value);
    model.value.states.push(state);
    if (!model.value.initial) model.value.initial = state.id;
    selection.value = { kind: "state", stateId: state.id };
  }

  draftRect.value = null;
  interaction.value = null;
  viewportEl.value?.releasePointerCapture(event.pointerId);
}

function onKeyDown(event: KeyboardEvent) {
  if (event.key !== "Delete" && event.key !== "Backspace") return;
  const target = event.target;
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
  if (!selection.value) return;

  if (selection.value.kind === "state") {
    const stateId = selection.value.stateId;
    model.value.states = model.value.states
      .filter((state) => state.id !== stateId)
      .map((state) => ({
        ...state,
        transitions: state.transitions.filter((transition) => transition.to !== stateId),
      }));
    if (model.value.initial === stateId) {
      model.value.initial = model.value.states[0]?.id ?? null;
    }
    selection.value = null;
    return;
  }

  const { stateId, transitionId } = selection.value;
  const state = model.value.states.find((item) => item.id === stateId);
  if (!state) return;
  state.transitions = state.transitions.filter((transition) => transition.id !== transitionId);
  selection.value = { kind: "state", stateId };
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

      <svg class="pointer-events-none absolute inset-0 overflow-visible" width="100%" height="100%">
        <defs>
          <marker
            id="fsm-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" class="fill-base-content/50" />
          </marker>
        </defs>

        <line
          v-if="draftLinkStart && draftLinkTo"
          :x1="draftLinkStart.x"
          :y1="draftLinkStart.y"
          :x2="draftLinkTo.x"
          :y2="draftLinkTo.y"
          class="stroke-primary"
          stroke-width="2"
          stroke-dasharray="6 4"
        />

        <g v-for="edge in edges" :key="edge.key">
          <line
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            :class="edge.selected ? 'stroke-primary' : 'stroke-base-content/40'"
            stroke-width="2"
            marker-end="url(#fsm-arrow)"
          />
          <rect
            :x="edge.mx - 40"
            :y="edge.my - 10"
            width="80"
            height="20"
            rx="4"
            class="fill-base-100"
            :class="edge.selected ? 'stroke-primary' : 'stroke-base-content/20'"
            stroke-width="1"
          />
          <text
            :x="edge.mx"
            :y="edge.my + 4"
            text-anchor="middle"
            class="fill-base-content text-[10px]"
          >
            {{ edge.event }}
          </text>
        </g>
      </svg>

      <div
        v-for="state in states"
        :key="state.id"
        class="fsm-state"
        :class="{
          'fsm-state--selected': selection?.kind === 'state' && selection.stateId === state.id,
          'fsm-state--initial': initial === state.id,
          'fsm-state--final': state.final,
        }"
        :style="{
          left: `${state.x}px`,
          top: `${state.y}px`,
          width: `${state.width}px`,
          height: `${state.height}px`,
        }"
      >
        <span class="truncate font-mono text-xs">{{ state.id }}</span>
        <span v-if="initial === state.id" class="badge badge-xs badge-primary">initial</span>
        <span v-if="state.final" class="badge badge-xs">final</span>
      </div>

      <div
        v-if="draftRect"
        class="fsm-state fsm-state--draft"
        :style="{
          left: `${draftRect.x}px`,
          top: `${draftRect.y}px`,
          width: `${draftRect.width}px`,
          height: `${draftRect.height}px`,
        }"
      />
    </div>

    <div class="pointer-events-none absolute bottom-3 right-3 rounded-box bg-base-100/90 px-3 py-1 text-xs shadow">
      {{ Math.round(model.viewport.zoom * 100) }}% · {{ states.length }} states
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

.canvas-viewport--draw,
.canvas-viewport--link {
  cursor: crosshair;
}

.canvas-grid {
  background-image: radial-gradient(
    circle,
    color-mix(in oklab, var(--color-base-content) 22%, transparent) 1px,
    transparent 1px
  );
}

.fsm-state {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: 2px solid color-mix(in oklab, var(--color-base-content) 18%, transparent);
  border-radius: 0.75rem;
  background: var(--color-base-100);
  box-shadow:
    0 1px 2px color-mix(in oklab, var(--color-base-content) 10%, transparent),
    0 8px 24px color-mix(in oklab, var(--color-base-content) 6%, transparent);
}

.fsm-state--selected {
  border-color: var(--color-primary);
  box-shadow:
    0 0 0 2px color-mix(in oklab, var(--color-primary) 25%, transparent),
    0 8px 24px color-mix(in oklab, var(--color-primary) 12%, transparent);
}

.fsm-state--initial {
  border-left-width: 4px;
  border-left-color: var(--color-primary);
}

.fsm-state--final {
  border-style: double;
  border-width: 4px;
}

.fsm-state--draft {
  border-style: dashed;
  opacity: 0.85;
  pointer-events: none;
}
</style>
