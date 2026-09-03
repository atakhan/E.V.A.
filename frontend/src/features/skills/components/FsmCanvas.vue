<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";
import {
  clamp,
  findResizeHandleAt,
  isValidRect,
  normalizeRect,
  resizeRectFromHandle,
  resizeHandlePosition,
  screenToWorld,
  snap,
  snapPoint,
  snapRect,
  stateDisplayName,
} from "@/features/skills/utils/canvasGeometry";
import {
  transitionIssueKey,
  worstSeverity,
} from "@/features/skills/utils/skillIssueIndex";
import type { SkillIssueMaps } from "@/features/skills/utils/skillIssueIndex";
import { formatUmlEntryLine, formatUmlTransitionLabel } from "@/features/skills/utils/fsmLabelFormat";
import {
  defaultAnchorsForPair,
  distanceToPolyline,
  EDGE_LABEL_NODE_RADIUS,
  EDGE_LABEL_LINE_GAP,
  magneticPointsForRect,
  normalizeMagneticAnchor,
  polylineToPath,
  routeEdge,
  snapEndpointToState,
  snapSideAnchorFromPoint,
  splitPolylineForLabel,
  polylineLength,
  type SideAnchor,
} from "@/features/skills/utils/edgeRouting";
import {
  GRID_SIZE,
  RESIZE_HANDLES,
  type CanvasTool,
  type DraftRect,
  type FsmEditorState,
  type FsmSelection,
  type FsmState,
  type FsmTransition,
  type Point,
  type ResizeHandle,
} from "@/features/skills/types/fsm";
import { createFsmState, createFsmTransition } from "@/features/skills/types/skill";

const props = defineProps<{
  activeTool: CanvasTool;
  issueMaps?: SkillIssueMaps;
  readOnly?: boolean;
}>();

const model = defineModel<FsmEditorState>({ required: true });
const selection = defineModel<FsmSelection>("selection", { default: null });

const viewportEl = useTemplateRef<HTMLElement>("viewport");

const draftRect = ref<DraftRect | null>(null);
const transitionFromId = ref<string | null>(null);
const transitionFromAnchor = ref<SideAnchor | null>(null);
const draftLinkTo = ref<Point | null>(null);

const HANDLE_RADIUS_PX = 7;

type EdgeDragPreview = {
  ownerStateId: string;
  transitionId: string;
  fromStateId: string;
  from: SideAnchor;
  toStateId: string;
  to: SideAnchor;
};

const edgeDragPreview = ref<EdgeDragPreview | null>(null);
const connectorTargetStateId = ref<string | null>(null);
const activeMagneticSnap = ref<{
  stateId: string;
  side: SideAnchor["side"];
  anchor: number;
} | null>(null);

type Interaction =
  | { kind: "pan"; startClient: Point; startPan: Point }
  | { kind: "draw"; anchor: Point }
  | { kind: "move"; id: string; offset: Point }
  | { kind: "resize"; id: string; handle: ResizeHandle; startRect: DraftRect }
  | { kind: "edge-endpoint"; endpoint: "from" | "to"; ownerStateId: string; transitionId: string };

const interaction = ref<Interaction | null>(null);

watch(
  () => props.activeTool,
  () => {
    transitionFromId.value = null;
    transitionFromAnchor.value = null;
    draftLinkTo.value = null;
    activeMagneticSnap.value = null;
    connectorTargetStateId.value = null;
  },
);

const states = computed(() => model.value.states);
const initial = computed(() => model.value.initial);

const selectedStateRect = computed(() => {
  if (selection.value?.kind !== "state") return null;
  const state = model.value.states.find((item) => item.id === selection.value!.stateId);
  if (!state) return null;
  return { x: state.x, y: state.y, width: state.width, height: state.height };
});

function stateSeverity(stateId: string): "error" | "warning" | null {
  const issues = props.issueMaps?.byState.get(stateId);
  if (!issues?.length) return null;
  return worstSeverity(issues) === "error" ? "error" : "warning";
}

function transitionSeverity(stateId: string, transitionId: string): "error" | "warning" | null {
  const issues = props.issueMaps?.byTransition.get(transitionIssueKey(stateId, transitionId));
  if (!issues?.length) return null;
  return worstSeverity(issues) === "error" ? "error" : "warning";
}

function stateIssueCount(stateId: string): number {
  return props.issueMaps?.byState.get(stateId)?.length ?? 0;
}

const draftLinkRoute = computed(() => {
  if (!transitionFromId.value || !transitionFromAnchor.value || !draftLinkTo.value) return null;
  const source = states.value.find((item) => item.id === transitionFromId.value);
  if (!source) return null;

  const targetAt = findStateAt(draftLinkTo.value);
  const target = targetAt ?? source;
  const isSelfLoop = target.id === source.id;
  const toAnchor = targetAt
    ? snapSideAnchorFromPoint(target, draftLinkTo.value)
    : snapSideAnchorFromPoint(source, draftLinkTo.value);

  return routeEdge(
    source,
    target,
    transitionFromAnchor.value,
    toAnchor,
    0,
    isSelfLoop,
  ).points;
});

function getTransition(ownerStateId: string, transitionId: string) {
  const owner = model.value.states.find((state) => state.id === ownerStateId);
  const transition = owner?.transitions.find((item) => item.id === transitionId);
  if (!owner || !transition) return null;
  return { owner, transition };
}

function resolveTransitionAnchors(
  source: FsmState,
  target: FsmState,
  transition: FsmTransition,
  parallelIndex: number,
): { from: SideAnchor; to: SideAnchor } {
  const isSelfLoop = source.id === target.id;
  if (transition.fromSide && transition.toSide) {
    return {
      from: {
        side: transition.fromSide,
        anchor: normalizeMagneticAnchor(transition.fromAnchor ?? 0.5),
      },
      to: {
        side: transition.toSide,
        anchor: normalizeMagneticAnchor(transition.toAnchor ?? 0.5),
      },
    };
  }
  return defaultAnchorsForPair(source, target, parallelIndex, isSelfLoop);
}

function routeForTransition(
  source: FsmState,
  target: FsmState,
  transition: FsmTransition,
  parallelIndex: number,
  preview: EdgeDragPreview | null,
): ReturnType<typeof routeEdge> {
  const usePreview = preview?.transitionId === transition.id;
  const fromState = usePreview
    ? (model.value.states.find((state) => state.id === preview.fromStateId) ?? source)
    : source;
  const toState = usePreview
    ? (model.value.states.find((state) => state.id === preview.toStateId) ?? target)
    : target;

  const anchors = usePreview
    ? { from: preview.from, to: preview.to }
    : resolveTransitionAnchors(source, target, transition, parallelIndex);

  return routeEdge(
    fromState,
    toState,
    anchors.from,
    anchors.to,
    parallelIndex,
    fromState.id === toState.id,
  );
}

const INITIAL_DOT_OFFSET = 28;

const initialMarker = computed(() => {
  const initialId = initial.value;
  if (!initialId) return null;
  const state = model.value.states.find((item) => item.id === initialId);
  if (!state) return null;
  const targetY = state.y + state.height / 2;
  return {
    dot: { x: state.x - INITIAL_DOT_OFFSET, y: targetY },
    target: { x: state.x, y: targetY },
  };
});

const edges = computed(() => {
  const byId = new Map(states.value.map((state) => [state.id, state]));
  const parallelCounts = new Map<string, number>();
  const result: Array<{
    key: string;
    stateId: string;
    transitionId: string;
    title: string;
    triggerLine: string;
    actionLine: string | null;
    labelLines: { triggerY: number; actionY?: number };
    points: Point[];
    beforePoints: Point[];
    afterPoints: Point[];
    labelAt: Point;
    labelWidth: number;
    labelHeight: number;
    nodeRadius: number;
    selected: boolean;
  }> = [];

  for (const state of states.value) {
    for (const transition of state.transitions) {
      const target = byId.get(transition.to);
      if (!target) continue;

      const pairKey = `${state.id}->${transition.to}`;
      const parallelIndex = parallelCounts.get(pairKey) ?? 0;
      parallelCounts.set(pairKey, parallelIndex + 1);

      const routed = routeForTransition(
        state,
        target,
        transition,
        parallelIndex,
        edgeDragPreview.value,
      );
      const labelAt = routed.labelAt;
      const selected =
        selection.value?.kind === "transition" &&
        selection.value.stateId === state.id &&
        selection.value.transitionId === transition.id;
      const label = formatUmlTransitionLabel(
        transition.event,
        transition.guard,
        transition.actions,
        selected,
        labelAt.y,
      );
      const lineGap = Math.min(
        EDGE_LABEL_LINE_GAP + label.width / 2,
        Math.max(EDGE_LABEL_LINE_GAP, polylineLength(routed.points) / 2 - 2),
      );
      const split = splitPolylineForLabel(routed.points, labelAt, lineGap);

      result.push({
        key: `${state.id}:${transition.id}`,
        stateId: state.id,
        transitionId: transition.id,
        title: label.title,
        triggerLine: label.triggerLine,
        actionLine: label.actionLine,
        labelLines: label.labelLines,
        points: routed.points,
        beforePoints: split.before,
        afterPoints: split.after,
        labelAt,
        labelWidth: label.width,
        labelHeight: label.height,
        nodeRadius: EDGE_LABEL_NODE_RADIUS,
        selected,
      });
    }
  }
  return result;
});

const showMagneticPoints = computed(
  () =>
    interaction.value?.kind === "edge-endpoint" ||
    (props.activeTool === "transition" && transitionFromId.value !== null),
);

const magneticPointMarkers = computed(() => {
  if (!showMagneticPoints.value) return [];

  const active = activeMagneticSnap.value;
  return states.value.flatMap((state) =>
    magneticPointsForRect(state).map((magnetic) => ({
      key: `${state.id}:${magnetic.side}:${magnetic.anchor}`,
      stateId: state.id,
      x: magnetic.point.x,
      y: magnetic.point.y,
      active:
        active?.stateId === state.id &&
        active.side === magnetic.side &&
        active.anchor === magnetic.anchor,
    })),
  );
});

const selectedEdgeHandles = computed(() => {
  const current = selection.value;
  if (current?.kind !== "transition") return null;
  const edge = edges.value.find(
    (item) => item.stateId === current.stateId && item.transitionId === current.transitionId,
  );
  if (!edge || edge.points.length < 2) return null;
  return {
    from: edge.points[0],
    to: edge.points[edge.points.length - 1],
    ownerStateId: edge.stateId,
    transitionId: edge.transitionId,
  };
});

const viewportClass = computed(() => {
  if (interaction.value?.kind === "edge-endpoint") return "canvas-viewport--edge-drag";
  if (interaction.value?.kind === "resize") return "canvas-viewport--resize";
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
    const dist = distanceToPolyline(point, edge.points);
    if (dist <= threshold) {
      return { stateId: edge.stateId, transitionId: edge.transitionId };
    }
  }
  return null;
}

function worldToScreen(point: Point): Point {
  const rect = getViewportRect();
  const zoom = model.value.viewport.zoom;
  return {
    x: rect.left + model.value.viewport.panX + point.x * zoom,
    y: rect.top + model.value.viewport.panY + point.y * zoom,
  };
}

function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest(".fsm-state__name-input, .fsm-state__name-button"));
}

function findSelectedResizeHandle(worldPoint: Point): ResizeHandle | null {
  if (props.activeTool !== "select") return null;
  if (selection.value?.kind !== "state") return null;
  const state = model.value.states.find((item) => item.id === selection.value!.stateId);
  if (!state) return null;
  const threshold = 10 / model.value.viewport.zoom;
  return findResizeHandleAt(
    { x: state.x, y: state.y, width: state.width, height: state.height },
    worldPoint,
    threshold,
  );
}
function findEndpointHandleAt(clientX: number, clientY: number): "from" | "to" | null {
  const handles = selectedEdgeHandles.value;
  if (!handles || props.activeTool !== "select") return null;

  const fromScreen = worldToScreen(handles.from);
  const toScreen = worldToScreen(handles.to);
  const threshold = HANDLE_RADIUS_PX + 4;

  const fromDist = Math.hypot(clientX - fromScreen.x, clientY - fromScreen.y);
  if (fromDist <= threshold) return "from";

  const toDist = Math.hypot(clientX - toScreen.x, clientY - toScreen.y);
  if (toDist <= threshold) return "to";

  return null;
}

function beginEdgeEndpointDrag(endpoint: "from" | "to", ownerStateId: string, transitionId: string) {
  const resolved = getTransition(ownerStateId, transitionId);
  if (!resolved) return;

  const { owner, transition } = resolved;
  const target = model.value.states.find((state) => state.id === transition.to);
  if (!target) return;

  let parallelIndex = 0;
  for (const item of owner.transitions) {
    if (item.id === transition.id) break;
    if (item.to === transition.to) parallelIndex += 1;
  }

  const anchors = resolveTransitionAnchors(owner, target, transition, parallelIndex);
  edgeDragPreview.value = {
    ownerStateId,
    transitionId,
    fromStateId: owner.id,
    from: anchors.from,
    toStateId: transition.to,
    to: anchors.to,
  };

  interaction.value = {
    kind: "edge-endpoint",
    endpoint,
    ownerStateId,
    transitionId,
  };
}

function updateEdgeEndpointDrag(clientX: number, clientY: number, endpoint: "from" | "to") {
  const preview = edgeDragPreview.value;
  if (!preview) return;

  const worldPoint = toWorld(clientX, clientY);
  const preferredStateId = endpoint === "from" ? preview.fromStateId : preview.toStateId;
  const snapped = snapEndpointToState(worldPoint, states.value, preferredStateId);
  if (!snapped) {
    connectorTargetStateId.value = null;
    activeMagneticSnap.value = null;
    return;
  }

  const state = states.value[snapped.stateIndex];
  connectorTargetStateId.value = state.id;
  activeMagneticSnap.value = {
    stateId: state.id,
    side: snapped.anchor.side,
    anchor: snapped.anchor.anchor,
  };

  if (endpoint === "from") {
    edgeDragPreview.value = {
      ...preview,
      fromStateId: state.id,
      from: snapped.anchor,
    };
  } else {
    edgeDragPreview.value = {
      ...preview,
      toStateId: state.id,
      to: snapped.anchor,
    };
  }
}

function commitEdgeEndpointDrag() {
  const preview = edgeDragPreview.value;
  if (!preview) return;

  const resolved = getTransition(preview.ownerStateId, preview.transitionId);
  if (!resolved) {
    edgeDragPreview.value = null;
    connectorTargetStateId.value = null;
    activeMagneticSnap.value = null;
    return;
  }

  let { owner, transition } = resolved;

  if (preview.fromStateId !== owner.id) {
    owner.transitions = owner.transitions.filter((item) => item.id !== transition.id);
    const nextOwner = model.value.states.find((state) => state.id === preview.fromStateId);
    if (!nextOwner) {
      owner.transitions.push(transition);
      edgeDragPreview.value = null;
      connectorTargetStateId.value = null;
      activeMagneticSnap.value = null;
      return;
    }
    nextOwner.transitions.push(transition);
    owner = nextOwner;
    selection.value = {
      kind: "transition",
      stateId: nextOwner.id,
      transitionId: transition.id,
    };
  }

  transition.fromSide = preview.from.side;
  transition.fromAnchor = preview.from.anchor;
  transition.to = preview.toStateId;
  transition.toSide = preview.to.side;
  transition.toAnchor = preview.to.anchor;

  edgeDragPreview.value = null;
  connectorTargetStateId.value = null;
  activeMagneticSnap.value = null;
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

  if (isInteractiveTarget(event.target)) return;

  const worldPoint = toSnappedWorld(event.clientX, event.clientY);
  const hit = findStateAt(worldPoint);

  if (props.readOnly) {
    if (hit) {
      selection.value = { kind: "state", stateId: hit.id };
    } else {
      interaction.value = {
        kind: "pan",
        startClient: { x: event.clientX, y: event.clientY },
        startPan: { x: model.value.viewport.panX, y: model.value.viewport.panY },
      };
      selection.value = null;
    }
    viewportEl.value?.setPointerCapture(event.pointerId);
    return;
  }

  if (props.activeTool === "select") {
    const resizeHandle = findSelectedResizeHandle(worldPoint);
    if (resizeHandle && selection.value?.kind === "state") {
      const state = model.value.states.find((item) => item.id === selection.value!.stateId);
      if (state) {
        interaction.value = {
          kind: "resize",
          id: state.id,
          handle: resizeHandle,
          startRect: {
            x: state.x,
            y: state.y,
            width: state.width,
            height: state.height,
          },
        };
        viewportEl.value?.setPointerCapture(event.pointerId);
        return;
      }
    }

    const handle = findEndpointHandleAt(event.clientX, event.clientY);
    if (handle && selectedEdgeHandles.value) {
      beginEdgeEndpointDrag(
        handle,
        selectedEdgeHandles.value.ownerStateId,
        selectedEdgeHandles.value.transitionId,
      );
      viewportEl.value?.setPointerCapture(event.pointerId);
      return;
    }
  }

  if (props.activeTool === "transition") {
    if (hit) {
      if (!transitionFromId.value) {
        transitionFromId.value = hit.id;
        transitionFromAnchor.value = snapSideAnchorFromPoint(hit, worldPoint);
        selection.value = { kind: "state", stateId: hit.id };
        draftLinkTo.value = worldPoint;
      } else {
        const source = model.value.states.find((state) => state.id === transitionFromId.value);
        if (source) {
          const toAnchor = snapSideAnchorFromPoint(hit, worldPoint);
          const fromAnchor = transitionFromAnchor.value ?? snapSideAnchorFromPoint(source, worldPoint);
          const transition = createFsmTransition(hit.id, {
            fromSide: fromAnchor.side,
            fromAnchor: fromAnchor.anchor,
            toSide: toAnchor.side,
            toAnchor: toAnchor.anchor,
          });
          source.transitions.push(transition);
          selection.value = {
            kind: "transition",
            stateId: source.id,
            transitionId: transition.id,
          };
        }
        transitionFromId.value = null;
        transitionFromAnchor.value = null;
        draftLinkTo.value = null;
        activeMagneticSnap.value = null;
        connectorTargetStateId.value = null;
      }
    } else {
      transitionFromId.value = null;
      transitionFromAnchor.value = null;
      draftLinkTo.value = null;
      activeMagneticSnap.value = null;
      connectorTargetStateId.value = null;
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
  if (props.readOnly) {
    const currentPan = interaction.value;
    if (currentPan?.kind === "pan") {
      model.value.viewport.panX = currentPan.startPan.x + (event.clientX - currentPan.startClient.x);
      model.value.viewport.panY = currentPan.startPan.y + (event.clientY - currentPan.startClient.y);
    }
    return;
  }
  if (props.activeTool === "transition" && transitionFromId.value) {
    const worldPoint = toWorld(event.clientX, event.clientY);
    draftLinkTo.value = worldPoint;
    const snapped = snapEndpointToState(worldPoint, states.value, transitionFromId.value);
    if (snapped) {
      const state = states.value[snapped.stateIndex];
      connectorTargetStateId.value = state.id;
      activeMagneticSnap.value = {
        stateId: state.id,
        side: snapped.anchor.side,
        anchor: snapped.anchor.anchor,
      };
    } else {
      connectorTargetStateId.value = null;
      activeMagneticSnap.value = null;
    }
  }

  const current = interaction.value;
  if (current?.kind === "edge-endpoint") {
    updateEdgeEndpointDrag(event.clientX, event.clientY, current.endpoint);
    return;
  }

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

  if (current.kind === "resize") {
    const state = model.value.states.find((item) => item.id === current.id);
    if (!state) return;
    const pointer = toWorld(event.clientX, event.clientY);
    const next = resizeRectFromHandle(current.startRect, current.handle, pointer);
    state.x = next.x;
    state.y = next.y;
    state.width = next.width;
    state.height = next.height;
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

  if (current?.kind === "edge-endpoint") {
    if (connectorTargetStateId.value) {
      commitEdgeEndpointDrag();
    } else {
      edgeDragPreview.value = null;
    }
    interaction.value = null;
    connectorTargetStateId.value = null;
    activeMagneticSnap.value = null;
    viewportEl.value?.releasePointerCapture(event.pointerId);
    return;
  }

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
  if (props.readOnly) return;
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

function focusState(stateId: string) {
  const state = model.value.states.find((item) => item.id === stateId);
  const viewport = viewportEl.value;
  if (state && viewport) {
    const rect = viewport.getBoundingClientRect();
    const zoom = model.value.viewport.zoom;
    model.value.viewport.panX = rect.width / 2 - (state.x + state.width / 2) * zoom;
    model.value.viewport.panY = rect.height / 2 - (state.y + state.height / 2) * zoom;
  }
  selection.value = { kind: "state", stateId };
}

function focusTransition(stateId: string, transitionId: string) {
  const state = model.value.states.find((item) => item.id === stateId);
  const viewport = viewportEl.value;
  if (state && viewport) {
    const rect = viewport.getBoundingClientRect();
    const zoom = model.value.viewport.zoom;
    model.value.viewport.panX = rect.width / 2 - (state.x + state.width / 2) * zoom;
    model.value.viewport.panY = rect.height / 2 - (state.y + state.height / 2) * zoom;
  }
  selection.value = { kind: "transition", stateId, transitionId };
}

defineExpose({ focusState, focusTransition });

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

        <path
          v-if="draftLinkRoute"
          :d="polylineToPath(draftLinkRoute)"
          class="stroke-primary"
          fill="none"
          stroke-width="2"
          stroke-dasharray="6 4"
        />

        <g v-if="initialMarker">
          <line
            :x1="initialMarker.dot.x"
            :y1="initialMarker.dot.y"
            :x2="initialMarker.target.x"
            :y2="initialMarker.target.y"
            class="stroke-base-content/45"
            stroke-width="2"
            marker-end="url(#fsm-arrow)"
          />
          <circle
            :cx="initialMarker.dot.x"
            :cy="initialMarker.dot.y"
            r="6"
            class="fill-base-content"
          />
        </g>

        <g v-for="edge in edges" :key="edge.key">
          <path
            v-if="edge.beforePoints.length >= 2"
            :d="polylineToPath(edge.beforePoints)"
            fill="none"
            stroke-width="2"
            :class="[
              edge.selected
                ? 'stroke-primary'
                : transitionSeverity(edge.stateId, edge.transitionId) === 'error'
                  ? 'stroke-error'
                  : transitionSeverity(edge.stateId, edge.transitionId) === 'warning'
                    ? 'stroke-warning'
                    : 'stroke-base-content/40',
            ]"
            :marker-end="edge.afterPoints.length >= 2 ? 'none' : 'url(#fsm-arrow)'"
          />
          <path
            v-if="edge.afterPoints.length >= 2"
            :d="polylineToPath(edge.afterPoints)"
            fill="none"
            stroke-width="2"
            :class="[
              edge.selected
                ? 'stroke-primary'
                : transitionSeverity(edge.stateId, edge.transitionId) === 'error'
                  ? 'stroke-error'
                  : transitionSeverity(edge.stateId, edge.transitionId) === 'warning'
                    ? 'stroke-warning'
                    : 'stroke-base-content/40',
            ]"
            marker-end="url(#fsm-arrow)"
          />
          <circle
            :cx="edge.labelAt.x"
            :cy="edge.labelAt.y"
            :r="edge.nodeRadius"
            class="fill-base-100 stroke-base-content/35"
            stroke-width="1.5"
            :class="edge.selected ? 'stroke-primary' : ''"
          />
          <rect
            :x="edge.labelAt.x - edge.labelWidth / 2"
            :y="edge.labelAt.y - edge.labelHeight / 2 - 1"
            :width="edge.labelWidth"
            :height="edge.labelHeight"
            rx="8"
            class="fill-base-100 stroke-base-content/20"
            stroke-width="1"
            :class="edge.selected ? 'stroke-primary' : ''"
          />
          <text text-anchor="middle" class="fill-base-content font-mono">
            <title>{{ edge.title }}</title>
            <tspan
              :x="edge.labelAt.x"
              :y="edge.labelLines.triggerY"
              class="text-[10px] font-medium"
            >
              {{ edge.triggerLine }}
            </tspan>
            <tspan
              v-if="edge.actionLine && edge.labelLines.actionY"
              :x="edge.labelAt.x"
              :y="edge.labelLines.actionY"
              class="fill-base-content/70 text-[9px]"
            >
              {{ edge.actionLine }}
            </tspan>
          </text>
        </g>
      </svg>

      <div
        v-for="state in states"
        :key="state.id"
        class="fsm-state"
        :class="{
          'fsm-state--selected': selection?.kind === 'state' && selection.stateId === state.id,
          'fsm-state--connector-target': connectorTargetStateId === state.id,
          'fsm-state--error': stateSeverity(state.id) === 'error',
          'fsm-state--warning': stateSeverity(state.id) === 'warning',
        }"
        :style="{
          left: `${state.x}px`,
          top: `${state.y}px`,
          width: `${state.width}px`,
          height: `${state.height}px`,
        }"
      >
        <input
          v-if="!readOnly && selection?.kind === 'state' && selection.stateId === state.id"
          v-model="state.name"
          type="text"
          class="fsm-state__name-input input input-xs w-full border-base-300/60 bg-base-100/90 px-2 font-medium"
          :placeholder="state.id"
          @pointerdown.stop
          @click.stop
        />
        <span
          v-else
          class="fsm-state__name truncate text-xs font-medium"
          :class="{ 'text-base-content/45': !state.name?.trim() }"
        >
          {{ stateDisplayName(state) }}
        </span>
        <p
          v-if="state.name?.trim() && selection?.kind === 'state' && selection.stateId === state.id"
          class="truncate font-mono text-[10px] text-base-content/40"
        >
          {{ state.id }}
        </p>
        <div v-if="state.onEnter.length > 0" class="fsm-state__on-enter">
          <span class="fsm-state__on-enter-label font-mono text-[9px] text-base-content/55">
            {{ formatUmlEntryLine(state.onEnter) }}
          </span>
        </div>
        <div
          v-if="state.final"
          class="fsm-state__final-icon"
          title="Final state"
          aria-label="Final state"
        >
          <svg viewBox="0 0 16 16" class="size-4 text-base-content/70" fill="none">
            <circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.5" />
            <circle cx="8" cy="8" r="3.5" fill="currentColor" />
          </svg>
        </div>
        <div class="fsm-state__badges flex flex-wrap gap-1">
        <span
          v-if="stateIssueCount(state.id) > 0"
          class="badge badge-xs"
          :class="stateSeverity(state.id) === 'error' ? 'badge-error' : 'badge-warning'"
        >
          {{ stateIssueCount(state.id) }}
        </span>
        </div>
      </div>

      <template v-if="selectedStateRect && activeTool === 'select' && !interaction && !readOnly">
        <div
          v-for="handle in RESIZE_HANDLES"
          :key="`${selection?.kind === 'state' ? selection.stateId : ''}:${handle}`"
          class="resize-handle"
          :class="`resize-handle--${handle}`"
          :style="{
            left: `${resizeHandlePosition(selectedStateRect, handle).x}px`,
            top: `${resizeHandlePosition(selectedStateRect, handle).y}px`,
          }"
        />
      </template>

      <template v-if="showMagneticPoints">
        <div
          v-for="marker in magneticPointMarkers"
          :key="marker.key"
          class="magnetic-point"
          :class="{ 'magnetic-point--active': marker.active }"
          :style="{
            left: `${marker.x}px`,
            top: `${marker.y}px`,
          }"
        />
      </template>

      <template v-if="selectedEdgeHandles && activeTool === 'select' && !readOnly">
        <div
          class="edge-handle edge-handle--from"
          :style="{
            left: `${selectedEdgeHandles.from.x}px`,
            top: `${selectedEdgeHandles.from.y}px`,
          }"
          title="Перетащите начало стрелки"
        />
        <div
          class="edge-handle edge-handle--to"
          :style="{
            left: `${selectedEdgeHandles.to.x}px`,
            top: `${selectedEdgeHandles.to.y}px`,
          }"
          title="Перетащите конец стрелки"
        />
      </template>

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

.canvas-viewport--edge-drag {
  cursor: grabbing;
}

.canvas-viewport--resize {
  cursor: nwse-resize;
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

.fsm-state--connector-target {
  border-color: var(--color-primary);
  box-shadow:
    0 0 0 3px color-mix(in oklab, var(--color-primary) 20%, transparent),
    0 8px 24px color-mix(in oklab, var(--color-primary) 10%, transparent);
}

.fsm-state--error {
  border-color: var(--color-error);
  box-shadow: 0 0 0 2px color-mix(in oklab, var(--color-error) 25%, transparent);
}

.fsm-state--warning {
  border-color: var(--color-warning);
  box-shadow: 0 0 0 2px color-mix(in oklab, var(--color-warning) 25%, transparent);
}

.edge-handle {
  position: absolute;
  z-index: 30;
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-primary);
  border-radius: 9999px;
  background: var(--color-base-100);
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 2px color-mix(in oklab, var(--color-primary) 20%, transparent);
  cursor: grab;
  pointer-events: none;
}

.edge-handle--to {
  background: var(--color-primary);
}

.magnetic-point {
  position: absolute;
  z-index: 25;
  width: 8px;
  height: 8px;
  border: 1.5px solid color-mix(in oklab, var(--color-primary) 70%, transparent);
  border-radius: 9999px;
  background: var(--color-base-100);
  transform: translate(-50%, -50%);
  pointer-events: none;
  opacity: 0.9;
  transition:
    width 120ms ease,
    height 120ms ease,
    background-color 120ms ease;
}

.magnetic-point--active {
  width: 11px;
  height: 11px;
  border-color: var(--color-primary);
  background: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-primary) 22%, transparent);
}

.fsm-state--draft {
  border-style: dashed;
  opacity: 0.85;
  pointer-events: none;
}

.fsm-state__name-input {
  pointer-events: auto;
}

.fsm-state__on-enter {
  width: 100%;
  margin-top: 0.15rem;
}

.fsm-state__on-enter-label {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fsm-state__final-icon {
  position: absolute;
  top: 0.35rem;
  right: 0.35rem;
  pointer-events: none;
}

.fsm-state__badges {
  margin-top: 0.15rem;
}

.resize-handle {
  position: absolute;
  z-index: 28;
  width: 10px;
  height: 10px;
  border: 2px solid var(--color-primary);
  border-radius: 2px;
  background: var(--color-base-100);
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 1px color-mix(in oklab, var(--color-primary) 20%, transparent);
  pointer-events: none;
}

.resize-handle--n,
.resize-handle--s {
  cursor: ns-resize;
}

.resize-handle--e,
.resize-handle--w {
  cursor: ew-resize;
}

.resize-handle--nw,
.resize-handle--se {
  cursor: nwse-resize;
}

.resize-handle--ne,
.resize-handle--sw {
  cursor: nesw-resize;
}
</style>
