<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from "vue";
import type { ActionDef } from "@/features/actions/types/action";
import type {
  BehaviorGraph,
  BehaviorNode,
  BehaviorSelection,
  BehaviorTool,
  CanvasMode,
} from "@/features/skills/types/behavior";
import { DEFAULT_NODE_SIZE } from "@/features/skills/types/behavior";
import type { Viewport } from "@/features/skills/types/fsm";
import StoryNodeCard from "@/features/skills/components/StoryNodeCard.vue";
import { clamp, screenToWorld, snap } from "@/features/skills/utils/canvasGeometry";
import { createId } from "@/shared/utils/id";
import { nodeRect, withNodeRect } from "@/features/skills/utils/behaviorLayout";
import { insertBehaviorStep, lastOpenNodeId } from "@/features/skills/utils/behaviorGraph";
import type { SkillIssueMaps } from "@/features/skills/utils/skillIssueIndex";

const props = defineProps<{
  mode: CanvasMode;
  activeTool: BehaviorTool;
  actions?: ActionDef[];
  issueMaps?: SkillIssueMaps;
  readOnly?: boolean;
  overlayByNode?: Record<string, "done" | "active" | "todo">;
}>();

const model = defineModel<BehaviorGraph>({ required: true });
const viewport = defineModel<Viewport>("viewport", {
  default: () => ({ panX: 0, panY: 0, zoom: 1 }),
});
const selection = defineModel<BehaviorSelection>("selection", { default: null });

const viewportEl = useTemplateRef<HTMLElement>("viewportEl");
const connectFrom = ref<string | null>(null);

const worldTransform = computed(
  () =>
    `translate(${viewport.value.panX}px, ${viewport.value.panY}px) scale(${viewport.value.zoom})`,
);

type Drag =
  | { kind: "pan"; startClient: { x: number; y: number }; startPan: Viewport }
  | { kind: "node"; nodeId: string; offset: { x: number; y: number } };

const drag = ref<Drag | null>(null);

const worldNodes = computed(() =>
  model.value.nodes.map((node) => ({
    node,
    rect: nodeRect(node, props.mode === "runtime" ? "story" : props.mode),
  })),
);

const links = computed(() => {
  const byId = new Map(worldNodes.value.map((item) => [item.node.id, item]));
  const result: Array<{
    key: string;
    label: string;
    from: { x: number; y: number };
    to: { x: number; y: number };
    selected: boolean;
  }> = [];
  for (const edge of model.value.edges) {
    const from = byId.get(edge.from);
    const to = byId.get(edge.to);
    if (!from || !to) continue;
    result.push({
      key: edge.id,
      label: edge.kind === "loop" ? "снова" : "",
      from: { x: from.rect.x + from.rect.width / 2, y: from.rect.y + from.rect.height },
      to: { x: to.rect.x + to.rect.width / 2, y: to.rect.y },
      selected: selection.value?.kind === "edge" && selection.value.edgeId === edge.id,
    });
  }
  for (const item of worldNodes.value) {
    if (item.node.type !== "decide") continue;
    for (const branch of item.node.branches) {
      const to = byId.get(branch.to);
      if (!to) continue;
      result.push({
        key: branch.id,
        label: branch.label,
        from: { x: item.rect.x + item.rect.width / 2, y: item.rect.y + item.rect.height },
        to: { x: to.rect.x + to.rect.width / 2, y: to.rect.y },
        selected:
          selection.value?.kind === "branch" &&
          selection.value.nodeId === item.node.id &&
          selection.value.branchId === branch.id,
      });
    }
  }
  return result;
});

function worldPoint(event: PointerEvent | MouseEvent) {
  const rect = viewportEl.value?.getBoundingClientRect();
  if (!rect) return { x: 0, y: 0 };
  return screenToWorld(
    event.clientX,
    event.clientY,
    rect,
    viewport.value.panX,
    viewport.value.panY,
    viewport.value.zoom,
  );
}

function onWheel(event: WheelEvent) {
  event.preventDefault();
  const rect = viewportEl.value?.getBoundingClientRect();
  if (!rect) return;
  const factor = event.deltaY < 0 ? 1.08 : 1 / 1.08;
  const zoom = viewport.value.zoom;
  const nextZoom = clamp(zoom * factor, 0.25, 2.5);
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  const worldX = (mouseX - viewport.value.panX) / zoom;
  const worldY = (mouseY - viewport.value.panY) / zoom;
  viewport.value = {
    zoom: nextZoom,
    panX: mouseX - worldX * nextZoom,
    panY: mouseY - worldY * nextZoom,
  };
}

function placeNode(partial: BehaviorNode, point: { x: number; y: number }) {
  const layoutRect = {
    x: snap(point.x - DEFAULT_NODE_SIZE.width / 2),
    y: snap(point.y - 20),
    width: DEFAULT_NODE_SIZE.width,
    height: DEFAULT_NODE_SIZE.height,
  };
  const node = withNodeRect(partial, props.mode === "logic" ? "logic" : "story", layoutRect);
  const fromId =
    selection.value?.kind === "node" ? selection.value.nodeId : lastOpenNodeId(model.value);
  model.value = insertBehaviorStep(model.value, node, fromId);
  selection.value = { kind: "node", nodeId: node.id };
}

function onPointerDown(event: PointerEvent) {
  if (event.button !== 0) return;
  const target = event.target as HTMLElement;
  if (target.closest("[data-node-id]")) return;
  const point = worldPoint(event);

  if (props.readOnly || props.activeTool === "select") {
    drag.value = {
      kind: "pan",
      startClient: { x: event.clientX, y: event.clientY },
      startPan: { ...viewport.value },
    };
    selection.value = null;
    return;
  }
  if (props.activeTool === "connect") {
    connectFrom.value = null;
    selection.value = null;
    return;
  }
  if (props.activeTool === "wait") {
    placeNode(
      {
        id: `node_${createId()}`,
        type: "wait",
        title: "Когда приходит новое сообщение",
        waitFor: { type: "input", event: "channel.message.received" },
      },
      point,
    );
    return;
  }
  if (props.activeTool === "do") {
    const action = props.actions?.[0];
    placeNode(
      {
        id: `node_${createId()}`,
        type: "do",
        title: action?.name ?? "Новое действие",
        actionId: action?.id ?? "",
      },
      point,
    );
    return;
  }
  if (props.activeTool === "decide") {
    placeNode(
      {
        id: `node_${createId()}`,
        type: "decide",
        title: "",
        question: "Мне хватает информации?",
        branches: [],
      },
      point,
    );
    return;
  }
  if (props.activeTool === "end") {
    placeNode(
      {
        id: `node_${createId()}`,
        type: "end",
        title: "Задача завершена",
      },
      point,
    );
  }
}

function onNodePointerDown(event: PointerEvent, node: BehaviorNode) {
  event.stopPropagation();
  if (props.readOnly) {
    selection.value = { kind: "node", nodeId: node.id };
    return;
  }
  if (props.activeTool === "connect") {
    if (!connectFrom.value) {
      connectFrom.value = node.id;
      selection.value = { kind: "node", nodeId: node.id };
      return;
    }
    if (connectFrom.value === node.id) {
      connectFrom.value = null;
      return;
    }
    connectNodes(connectFrom.value, node.id);
    connectFrom.value = null;
    return;
  }
  selection.value = { kind: "node", nodeId: node.id };
  const rect = nodeRect(node, props.mode === "runtime" ? "story" : props.mode);
  const point = worldPoint(event);
  drag.value = {
    kind: "node",
    nodeId: node.id,
    offset: { x: point.x - rect.x, y: point.y - rect.y },
  };
}

function connectNodes(fromId: string, toId: string) {
  const from = model.value.nodes.find((item) => item.id === fromId);
  if (!from) return;
  if (from.type === "decide") {
    model.value = {
      ...model.value,
      nodes: model.value.nodes.map((item) => {
        if (item.id !== fromId || item.type !== "decide") return item;
        const label = item.branches.length === 0 ? "Да" : item.branches.length === 1 ? "Нет" : `Ветка ${item.branches.length + 1}`;
        return {
          ...item,
          branches: [
            ...item.branches,
            { id: `edge_${createId()}`, label, guard: "", to: toId },
          ],
        };
      }),
    };
    return;
  }
  const existing = model.value.edges.filter((edge) => edge.from !== fromId);
  existing.push({
    id: `edge_${createId()}`,
    from: fromId,
    to: toId,
    kind: toId === model.value.entry ? "loop" : "next",
  });
  model.value = { ...model.value, edges: existing };
}

function onPointerMove(event: PointerEvent) {
  const current = drag.value;
  if (!current) return;
  if (current.kind === "pan") {
    viewport.value = {
      ...viewport.value,
      panX: current.startPan.panX + (event.clientX - current.startClient.x),
      panY: current.startPan.panY + (event.clientY - current.startClient.y),
    };
    return;
  }
  if (props.readOnly) return;
  const point = worldPoint(event);
  model.value = {
    ...model.value,
    nodes: model.value.nodes.map((node) => {
      if (node.id !== current.nodeId) return node;
      return withNodeRect(node, props.mode === "logic" ? "logic" : "story", {
        x: snap(point.x - current.offset.x),
        y: snap(point.y - current.offset.y),
      });
    }),
  };
}

function onPointerUp() {
  drag.value = null;
}

function onKeyDown(event: KeyboardEvent) {
  if (props.readOnly) return;
  if (event.key !== "Delete" && event.key !== "Backspace") return;
  const current = selection.value;
  if (!current) return;
  if (current.kind === "node") {
    model.value = {
      ...model.value,
      nodes: model.value.nodes.filter((node) => node.id !== current.nodeId),
      edges: model.value.edges.filter(
        (edge) => edge.from !== current.nodeId && edge.to !== current.nodeId,
      ),
      entry: model.value.entry === current.nodeId ? "" : model.value.entry,
    };
    selection.value = null;
  }
  if (current.kind === "edge") {
    model.value = {
      ...model.value,
      edges: model.value.edges.filter((edge) => edge.id !== current.edgeId),
    };
    selection.value = null;
  }
}

onMounted(() => {
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
  window.addEventListener("keydown", onKeyDown);
});
onUnmounted(() => {
  window.removeEventListener("pointermove", onPointerMove);
  window.removeEventListener("pointerup", onPointerUp);
  window.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
  <div
    ref="viewportEl"
    class="absolute inset-0 overflow-hidden bg-base-200/40"
    @wheel.prevent="onWheel"
    @pointerdown="onPointerDown"
  >
    <div class="absolute left-0 top-0 origin-top-left" :style="{ transform: worldTransform }">
      <svg class="overflow-visible" width="1" height="1">
        <defs>
          <marker id="bh-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" class="fill-base-content/50" />
          </marker>
        </defs>
        <line
          v-for="link in links"
          :key="link.key"
          :x1="link.from.x"
          :y1="link.from.y"
          :x2="link.to.x"
          :y2="link.to.y"
          class="stroke-base-content/40"
          :class="{ 'stroke-primary': link.selected }"
          stroke-width="2"
          marker-end="url(#bh-arrow)"
        />
      </svg>
      <p
        v-for="link in links"
        :key="`${link.key}-label`"
        class="pointer-events-none absolute text-[10px] text-base-content/60"
        :style="{
          left: `${(link.from.x + link.to.x) / 2}px`,
          top: `${(link.from.y + link.to.y) / 2}px`,
        }"
      >
        {{ link.label }}
      </p>
      <div
        v-for="item in worldNodes"
        :key="item.node.id"
        data-node-id
        class="absolute"
        :style="{
          left: `${item.rect.x}px`,
          top: `${item.rect.y}px`,
          width: `${item.rect.width}px`,
        }"
        @pointerdown="onNodePointerDown($event, item.node)"
      >
        <StoryNodeCard
          :node="item.node"
          :mode="mode === 'runtime' ? 'story' : mode"
          :selected="selection?.kind === 'node' && selection.nodeId === item.node.id"
          :actions="actions"
          :issue-maps="issueMaps"
          :overlay="overlayByNode?.[item.node.id] ?? (mode === 'runtime' ? 'todo' : 'idle')"
        />
      </div>
    </div>
    <p class="pointer-events-none absolute bottom-3 right-3 text-xs text-base-content/50">
      {{ Math.round(viewport.zoom * 100) }}% · {{ model.nodes.length }} шагов
    </p>
  </div>
</template>
