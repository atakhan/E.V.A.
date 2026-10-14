<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";
import type { WorldLinkStatus } from "@/features/agents/utils/evaluateWorldLink";
import {
  ADD_SKILL_SLOT,
  WORLD_ADDRESS_HEIGHT,
  WORLD_ADDRESS_WIDTH,
  WORLD_KIND_HEIGHT,
  WORLD_KIND_WIDTH,
  WORLD_PORT_GAP,
  WORLD_PORT_SIZE,
  type ConstructorSkillNode,
} from "@/features/constructor/types/constructor";

export interface CanvasWorldKind {
  toolId: string;
  name: string;
  connected: boolean;
  status: WorldLinkStatus;
  reason: string;
  x: number;
  y: number;
}

export interface CanvasWorldAddress {
  id: string;
  toolId: string;
  name: string;
  x: number;
  y: number;
}

const props = withDefaults(
  defineProps<{
    nodes?: Array<ConstructorSkillNode & { name: string }>;
    selectedNodeId?: string | null;
    selectedKindToolId?: string | null;
    selectedAddressId?: string | null;
    addSkillSlot?: { x: number; y: number };
    addKindSlot?: { x: number; y: number };
    worldKinds?: CanvasWorldKind[];
    worldAddresses?: CanvasWorldAddress[];
  }>(),
  {
    nodes: () => [],
    selectedNodeId: null,
    selectedKindToolId: null,
    selectedAddressId: null,
    addSkillSlot: () => ({ ...ADD_SKILL_SLOT }),
    addKindSlot: () => ({ x: -300, y: 0 }),
    worldKinds: () => [],
    worldAddresses: () => [],
  },
);

const emit = defineEmits<{
  createSkill: [];
  selectNode: [nodeId: string];
  clearSelection: [];
  viewport: [payload: { panX: number; panY: number; zoom: number }];
  disconnectKind: [toolId: string];
  selectKind: [toolId: string];
  addKind: [];
  addAddress: [toolId: string];
  removeAddress: [addressId: string];
  selectAddress: [addressId: string];
}>();

const GRID_SIZE = 20;
const AGENT_SIZE = 88;
const ADD_BTN_WIDTH = 168;
const ADD_BTN_HEIGHT = 48;

const panX = ref(0);
const panY = ref(0);
const zoom = ref(1);

const viewportEl = useTemplateRef<HTMLElement>("viewport");

type PanDrag = {
  pointerId: number;
  startClient: { x: number; y: number };
  startPan: { x: number; y: number };
  moved: boolean;
};

const panDrag = ref<PanDrag | null>(null);

const addKindButtonStyle = computed(() => ({
  left: `${props.addKindSlot.x - WORLD_KIND_WIDTH / 2}px`,
  top: `${props.addKindSlot.y - ADD_BTN_HEIGHT / 2}px`,
  width: `${WORLD_KIND_WIDTH}px`,
  height: `${ADD_BTN_HEIGHT}px`,
}));

const viewportStyle = computed(() => {
  const size = GRID_SIZE * zoom.value;
  return {
    backgroundImage:
      "radial-gradient(circle, color-mix(in oklab, var(--color-base-content) 18%, transparent) 1px, transparent 1px)",
    backgroundSize: `${size}px ${size}px`,
    backgroundPosition: `${panX.value}px ${panY.value}px`,
    cursor: panDrag.value ? "grabbing" : "grab",
  };
});

const worldStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
  transformOrigin: "0 0",
}));

const addButtonStyle = computed(() => ({
  left: `${props.addSkillSlot.x - ADD_BTN_WIDTH / 2}px`,
  top: `${props.addSkillSlot.y - ADD_BTN_HEIGHT / 2}px`,
  width: `${ADD_BTN_WIDTH}px`,
  height: `${ADD_BTN_HEIGHT}px`,
}));

function curvePath(toX: number, toY: number): string {
  const len = Math.hypot(toX, toY) || 1;
  const rim = AGENT_SIZE / 2 + 4;
  const startX = (toX / len) * rim;
  const startY = (toY / len) * rim;
  const midX = toX * 0.5;
  const midY = toY * 0.5;
  const bulge = 36;
  const nx = -toY / len;
  const ny = toX / len;
  const cx = midX + nx * bulge;
  const cy = midY + ny * bulge;
  return `M ${startX} ${startY} Q ${cx} ${cy} ${toX} ${toY}`;
}

function cableClass(status: WorldLinkStatus): string {
  if (status === "green") return "stroke-success";
  if (status === "yellow") return "stroke-warning";
  if (status === "red") return "stroke-error";
  return "stroke-base-content/25";
}

const addSkillPath = computed(() => curvePath(props.addSkillSlot.x, props.addSkillSlot.y));

const skillPaths = computed(() =>
  props.nodes.map((node) => ({
    id: node.id,
    d: curvePath(node.x + node.width / 2, node.y + node.height / 2),
  })),
);

const connectedKindCables = computed(() =>
  props.worldKinds
    .filter((kind) => kind.connected)
    .map((kind) => ({
      id: kind.toolId,
      d: curvePath(kind.x, kind.y),
      status: kind.status,
    })),
);

const addressLinks = computed(() => {
  const kindByTool = new Map(props.worldKinds.map((kind) => [kind.toolId, kind]));
  return props.worldAddresses
    .map((address) => {
      const kind = kindByTool.get(address.toolId);
      if (!kind?.connected) return null;
      return {
        id: address.id,
        d: `M ${address.x} ${address.y} L ${kind.x} ${kind.y}`,
      };
    })
    .filter((item): item is { id: string; d: string } => item !== null);
});

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function centerOnOrigin(resetZoom = false) {
  const rect = viewportEl.value?.getBoundingClientRect();
  if (!rect) return;
  if (resetZoom) zoom.value = 1;
  panX.value = rect.width / 2;
  panY.value = rect.height / 2;
}

function centerOnNode(node: ConstructorSkillNode, resetZoom = false) {
  const rect = viewportEl.value?.getBoundingClientRect();
  if (!rect) return;
  if (resetZoom) zoom.value = 1;
  panX.value = rect.width / 2 - (node.x + node.width / 2) * zoom.value;
  panY.value = rect.height / 2 - (node.y + node.height / 2) * zoom.value;
}

function onWheel(event: WheelEvent) {
  event.preventDefault();
  const rect = viewportEl.value?.getBoundingClientRect();
  if (!rect) return;

  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  const factor = event.deltaY < 0 ? 1.08 : 1 / 1.08;
  const nextZoom = clamp(zoom.value * factor, 0.25, 2.5);
  const worldX = (mouseX - panX.value) / zoom.value;
  const worldY = (mouseY - panY.value) / zoom.value;

  zoom.value = nextZoom;
  panX.value = mouseX - worldX * nextZoom;
  panY.value = mouseY - worldY * nextZoom;
}

function onPointerDown(event: PointerEvent) {
  if (event.button !== 0 && event.button !== 1) return;
  if (event.target instanceof Element && event.target.closest("[data-canvas-ui]")) return;

  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) return;

  panDrag.value = {
    pointerId: event.pointerId,
    startClient: { x: event.clientX, y: event.clientY },
    startPan: { x: panX.value, y: panY.value },
    moved: false,
  };
  target.setPointerCapture(event.pointerId);
}

function onPointerMove(event: PointerEvent) {
  const drag = panDrag.value;
  if (!drag || drag.pointerId !== event.pointerId) return;
  const dx = event.clientX - drag.startClient.x;
  const dy = event.clientY - drag.startClient.y;
  if (Math.abs(dx) > 2 || Math.abs(dy) > 2) drag.moved = true;
  panX.value = drag.startPan.x + dx;
  panY.value = drag.startPan.y + dy;
}

function onPointerUp(event: PointerEvent) {
  const drag = panDrag.value;
  if (!drag || drag.pointerId !== event.pointerId) return;
  const wasClick = !drag.moved;
  panDrag.value = null;
  const target = event.currentTarget;
  if (target instanceof HTMLElement && target.hasPointerCapture(event.pointerId)) {
    target.releasePointerCapture(event.pointerId);
  }
  if (wasClick && event.button === 0) {
    emit("clearSelection");
  }
}

watch(
  [panX, panY, zoom],
  ([x, y, z]) => {
    emit("viewport", { panX: x, panY: y, zoom: z });
  },
  { immediate: true },
);

onMounted(async () => {
  await nextTick();
  centerOnOrigin(true);
});

onUnmounted(() => {
  panDrag.value = null;
});

defineExpose({
  centerOnOrigin,
  centerOnNode,
});
</script>

<template>
  <div
    ref="viewport"
    class="relative h-full w-full touch-none overflow-hidden bg-base-300 select-none"
    :style="viewportStyle"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @contextmenu.prevent
  >
    <div class="pointer-events-none absolute inset-0" :style="worldStyle">
      <svg
        class="pointer-events-none absolute overflow-visible"
        width="1"
        height="1"
        aria-hidden="true"
      >
        <path
          v-for="link in addressLinks"
          :key="`addr-${link.id}`"
          :d="link.d"
          fill="none"
          class="stroke-base-content/20"
          stroke-width="1.5"
          stroke-dasharray="4 4"
          stroke-linecap="round"
        />
        <path
          v-for="cable in connectedKindCables"
          :key="`cable-hit-${cable.id}`"
          :d="cable.d"
          fill="none"
          stroke="transparent"
          stroke-width="16"
          stroke-linecap="round"
          class="pointer-events-auto cursor-pointer"
          @pointerdown.stop
          @click.stop="emit('selectKind', cable.id)"
        />
        <path
          v-for="cable in connectedKindCables"
          :key="`cable-${cable.id}`"
          :d="cable.d"
          fill="none"
          :class="cableClass(cable.status)"
          stroke-width="3"
          stroke-linecap="round"
          class="pointer-events-none"
        />
        <path
          v-for="link in skillPaths"
          :key="link.id"
          :d="link.d"
          fill="none"
          class="stroke-base-content/25"
          stroke-width="2"
          stroke-dasharray="6 6"
          stroke-linecap="round"
        />
        <path
          :d="addSkillPath"
          fill="none"
          class="stroke-base-content/35"
          stroke-width="2"
          stroke-dasharray="6 6"
          stroke-linecap="round"
        />
      </svg>

      <button
        type="button"
        data-canvas-ui
        class="pointer-events-auto absolute flex items-center justify-center gap-1.5 rounded-2xl border-2 border-dashed border-base-content/35 bg-base-100/40 text-sm font-medium text-base-content/70 backdrop-blur-sm transition hover:border-primary/60 hover:bg-base-100/80 hover:text-base-content"
        :style="addKindButtonStyle"
        title="Добавить канал"
        @click="emit('addKind')"
        @pointerdown.stop
      >
        <svg
          viewBox="0 0 24 24"
          class="size-4 shrink-0"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <path stroke-linecap="round" d="M12 5v14M5 12h14" />
        </svg>
        Добавить
      </button>

      <!-- Connected world kinds -->
      <div
        v-for="kind in worldKinds"
        :key="kind.toolId"
        data-canvas-ui
        class="pointer-events-auto absolute"
        :style="{
          left: `${kind.x - WORLD_KIND_WIDTH / 2}px`,
          top: `${kind.y - WORLD_KIND_HEIGHT / 2}px`,
          width: `${WORLD_KIND_WIDTH}px`,
        }"
        @pointerdown.stop
      >
        <div class="relative flex flex-col items-stretch gap-1">
          <div
            class="flex h-14 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-base-300 bg-base-100 px-2 text-center text-xs font-semibold text-base-content shadow-md hover:border-primary/50"
            :class="selectedKindToolId === kind.toolId ? 'ring-2 ring-primary/40' : ''"
            :title="`${kind.reason} · клик — настроить канал`"
            @click="emit('selectKind', kind.toolId)"
          >
            <span class="line-clamp-2">{{ kind.name }}</span>
          </div>

          <!-- Add address port (left of kind) -->
          <button
            v-if="kind.connected"
            type="button"
            class="absolute top-1/2 flex -translate-y-1/2 items-center justify-center rounded-full border border-base-content/30 bg-base-200/90 text-base-content/45 shadow-sm transition hover:border-primary/50 hover:text-primary"
            :style="{
              left: `${-(WORLD_PORT_GAP + WORLD_PORT_SIZE)}px`,
              width: `${WORLD_PORT_SIZE}px`,
              height: `${WORLD_PORT_SIZE}px`,
            }"
            title="Добавить адрес"
            aria-label="Добавить адрес"
            @click="emit('addAddress', kind.toolId)"
          >
            <svg viewBox="0 0 24 24" class="size-2.5" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true">
              <path stroke-linecap="round" d="M12 5v14M5 12h14" />
            </svg>
          </button>

          <button
            v-if="kind.connected"
            type="button"
            class="btn btn-ghost btn-xs text-base-content/50"
            title="Отключить канал"
            aria-label="Отключить канал"
            @click="emit('disconnectKind', kind.toolId)"
          >
            Отключить
          </button>
        </div>
      </div>

      <!-- Addresses -->
      <div
        v-for="address in worldAddresses"
        :key="address.id"
        data-canvas-ui
        class="group pointer-events-auto absolute flex cursor-pointer items-center justify-center rounded-xl border bg-base-100/90 px-2 text-center text-[11px] font-medium shadow-sm transition hover:border-primary/50"
        :class="
          selectedAddressId === address.id
            ? 'border-primary ring-2 ring-primary/40'
            : 'border-base-300/70'
        "
        :style="{
          left: `${address.x - WORLD_ADDRESS_WIDTH / 2}px`,
          top: `${address.y - WORLD_ADDRESS_HEIGHT / 2}px`,
          width: `${WORLD_ADDRESS_WIDTH}px`,
          height: `${WORLD_ADDRESS_HEIGHT}px`,
        }"
        :title="'Клик — настроить адрес'"
        @pointerdown.stop
        @click="emit('selectAddress', address.id)"
      >
        <span class="line-clamp-2 px-3">{{ address.name }}</span>
        <button
          type="button"
          class="absolute -right-1.5 -top-1.5 flex size-5 items-center justify-center rounded-full border border-base-300 bg-base-100 text-[10px] text-base-content/45 opacity-0 shadow-sm transition hover:border-error/50 hover:text-error group-hover:opacity-100"
          title="Удалить адрес"
          aria-label="Удалить адрес"
          @click.stop="emit('removeAddress', address.id)"
        >
          ✕
        </button>
      </div>

      <button
        type="button"
        data-canvas-ui
        class="pointer-events-auto absolute flex items-center justify-center gap-1.5 rounded-2xl border-2 border-dashed border-base-content/35 bg-base-100/40 text-sm font-medium text-base-content/70 backdrop-blur-sm transition hover:border-primary/60 hover:bg-base-100/80 hover:text-base-content"
        :style="addButtonStyle"
        @click="emit('createSkill')"
        @pointerdown.stop
      >
        <svg
          viewBox="0 0 24 24"
          class="size-4 shrink-0"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <path stroke-linecap="round" d="M12 5v14M5 12h14" />
        </svg>
        Добавить навык
      </button>

      <button
        v-for="node in props.nodes"
        :key="node.id"
        type="button"
        data-canvas-ui
        class="pointer-events-auto absolute flex items-center justify-center rounded-2xl border px-4 text-center text-sm font-semibold shadow-md transition"
        :class="
          selectedNodeId === node.id
            ? 'border-primary bg-base-100 text-base-content ring-2 ring-primary/40'
            : 'border-base-300/70 bg-base-100/95 text-base-content hover:border-primary/50'
        "
        :style="{
          left: `${node.x}px`,
          top: `${node.y}px`,
          width: `${node.width}px`,
          height: `${node.height}px`,
        }"
        @click="emit('selectNode', node.id)"
        @pointerdown.stop
      >
        <span class="line-clamp-2">{{ node.name }}</span>
      </button>
    </div>

    <button
      type="button"
      class="btn btn-circle btn-md absolute bottom-4 left-4 z-10 border border-base-300/60 bg-base-100/90 shadow-lg backdrop-blur-sm"
      data-canvas-ui
      title="К центру холста"
      aria-label="К центру холста"
      @click="centerOnOrigin(true)"
      @pointerdown.stop
    >
      <svg
        viewBox="0 0 24 24"
        class="size-5"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    </button>

    <div
      class="pointer-events-none absolute bottom-4 right-4 rounded-box border border-base-300/60 bg-base-100/90 px-2 py-1 font-mono text-xs text-base-content/70 shadow-lg backdrop-blur-sm"
    >
      {{ Math.round(zoom * 100) }}%
    </div>
  </div>
</template>
