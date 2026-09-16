import type { FsmEditorState, FsmState, FsmTransition, SkillParam, FlowDirection } from "@/features/skills/types/fsm";
import {
  DEFAULT_STATE_HEIGHT,
  DEFAULT_STATE_WIDTH,
  GRID_SIZE,
} from "@/features/skills/types/fsm";
import type { BehaviorGraph } from "@/features/skills/types/behavior";
import { compileBehavior } from "@/features/skills/utils/behaviorCompile";
import { createId } from "@/shared/utils/id";

export interface Skill {
  id: string;
  name: string;
  description: string;
  version: string;
  createdAt: string;
  updatedAt: string;
  initial: string | null;
  params: SkillParam[];
  states: FsmState[];
  viewport: { panX: number; panY: number; zoom: number };
  flowDirection?: FlowDirection;
}

/** Incoming document may still carry a leftover Behavior Graph from drafts. */
type SkillIncoming = Skill & {
  behavior?: BehaviorGraph;
  rectangles?: LegacyCanvasSkill["rectangles"];
};

/** Legacy Phase 0 canvas document. */
interface LegacyCanvasSkill {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  rectangles?: Array<{
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
  viewport?: { panX: number; panY: number; zoom: number };
  initial?: string | null;
  params?: SkillParam[];
  states?: FsmState[];
  version?: string;
  behavior?: BehaviorGraph;
  flowDirection?: FlowDirection;
}

export function createEmptyFsmEditorState(): FsmEditorState {
  return {
    initial: null,
    params: [],
    states: [],
    viewport: { panX: 0, panY: 0, zoom: 1 },
    flowDirection: "vertical",
  };
}

export function createEmptySkill(partial?: Partial<Skill> & { name: string }): Skill {
  const now = new Date().toISOString();
  return {
    id: partial?.id ?? createId(),
    name: partial?.name ?? "Skill",
    description: partial?.description ?? "",
    version: partial?.version ?? "0.1.0",
    createdAt: partial?.createdAt ?? now,
    updatedAt: partial?.updatedAt ?? now,
    initial: partial?.initial ?? null,
    params: partial?.params ?? [],
    states: partial?.states ?? [],
    viewport: partial?.viewport ?? { panX: 0, panY: 0, zoom: 1 },
    flowDirection: partial?.flowDirection ?? "vertical",
  };
}

function nextStateId(existing: FsmState[]): string {
  let n = existing.length + 1;
  const used = new Set(existing.map((state) => state.id));
  while (used.has(`state_${n}`)) n += 1;
  return `state_${n}`;
}

export function createFsmState(
  existing: FsmState[],
  layout: { x: number; y: number; width: number; height: number },
): FsmState {
  return {
    id: nextStateId(existing),
    onEnter: [],
    final: false,
    transitions: [],
    x: layout.x,
    y: layout.y,
    width: layout.width,
    height: layout.height,
  };
}

export function createFsmTransition(
  to: string,
  partial?: Partial<Pick<FsmTransition, "event" | "fromSide" | "toSide" | "fromAnchor" | "toAnchor">>,
): FsmTransition {
  return {
    id: createId(),
    event: partial?.event ?? "event",
    guard: "",
    actions: [],
    to,
    fromSide: partial?.fromSide,
    toSide: partial?.toSide,
    fromAnchor: partial?.fromAnchor,
    toAnchor: partial?.toAnchor,
  };
}

function migrateRectanglesToStates(raw: LegacyCanvasSkill): FsmState[] {
  const rectangles = raw.rectangles ?? [];
  return rectangles.map((rect, index) => ({
    id: `state_${index + 1}`,
    onEnter: [],
    final: false,
    transitions: [],
    x: rect.x,
    y: rect.y,
    width: Math.max(DEFAULT_STATE_WIDTH, rect.width),
    height: Math.max(DEFAULT_STATE_HEIGHT, rect.height),
  }));
}

function normalizeRectSide(raw: unknown): FsmTransition["fromSide"] {
  if (raw === "top" || raw === "right" || raw === "bottom" || raw === "left") {
    return raw;
  }
  return undefined;
}

function normalizeAnchor(raw: unknown): number | undefined {
  if (typeof raw !== "number" || Number.isNaN(raw)) return undefined;
  return Math.min(1, Math.max(0, raw));
}

function normalizeWaypoints(raw: unknown): FsmTransition["waypoints"] {
  if (!Array.isArray(raw)) return undefined;
  const points = raw
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const point = item as { x?: unknown; y?: unknown };
      if (typeof point.x !== "number" || typeof point.y !== "number") return null;
      if (Number.isNaN(point.x) || Number.isNaN(point.y)) return null;
      return { x: point.x, y: point.y };
    })
    .filter((item): item is { x: number; y: number } => item !== null);
  return points.length > 0 ? points : undefined;
}

function normalizeTransition(raw: Partial<FsmTransition>): FsmTransition {
  return {
    id: raw.id || createId(),
    event: (raw.event || "event").trim() || "event",
    guard: raw.guard ?? "",
    actions: Array.isArray(raw.actions)
      ? raw.actions.map((item) => String(item).trim()).filter(Boolean)
      : [],
    to: raw.to || "",
    fromSide: normalizeRectSide(raw.fromSide),
    toSide: normalizeRectSide(raw.toSide),
    fromAnchor: normalizeAnchor(raw.fromAnchor),
    toAnchor: normalizeAnchor(raw.toAnchor),
    waypoints: normalizeWaypoints(raw.waypoints),
    routingMode: raw.routingMode === "manual_assisted" ? "manual_assisted" : "automatic",
    originNodeId: typeof raw.originNodeId === "string" ? raw.originNodeId : undefined,
    originEdgeId: typeof raw.originEdgeId === "string" ? raw.originEdgeId : undefined,
  };
}

function normalizeState(raw: Partial<FsmState>, fallbackId: string): FsmState {
  const name = typeof raw.name === "string" ? raw.name.trim() : "";
  return {
    id: (raw.id || fallbackId).trim() || fallbackId,
    name: name || undefined,
    onEnter: Array.isArray(raw.onEnter)
      ? raw.onEnter.map((item) => String(item).trim()).filter(Boolean)
      : [],
    final: Boolean(raw.final),
    transitions: Array.isArray(raw.transitions)
      ? raw.transitions.map((item) => normalizeTransition(item))
      : [],
    x: typeof raw.x === "number" ? raw.x : 0,
    y: typeof raw.y === "number" ? raw.y : 0,
    width: typeof raw.width === "number" ? raw.width : DEFAULT_STATE_WIDTH,
    height: typeof raw.height === "number" ? raw.height : DEFAULT_STATE_HEIGHT,
    originNodeId: typeof raw.originNodeId === "string" ? raw.originNodeId : undefined,
  };
}

function flattenLeftoverBehavior(raw: SkillIncoming | LegacyCanvasSkill): {
  states: FsmState[];
  initial: string | null;
} | null {
  const behavior = raw.behavior;
  if (!behavior || !Array.isArray(behavior.nodes) || behavior.nodes.length === 0) {
    return null;
  }
  const compiled = compileBehavior(behavior);
  if (!compiled.ok) return null;
  return {
    states: compiled.artifact.states.map((state, index) => normalizeState(state, `state_${index + 1}`)),
    initial: compiled.artifact.initial || null,
  };
}

export function skillFromLegacyCanvas(canvas: LegacyCanvasSkill): Skill {
  return normalizeSkill(canvas);
}

export function normalizeSkill(raw: LegacyCanvasSkill | SkillIncoming): Skill {
  const flattened = flattenLeftoverBehavior(raw);
  let states: FsmState[] = flattened
    ? flattened.states
    : Array.isArray(raw.states)
      ? raw.states.map((state, index) => normalizeState(state, `state_${index + 1}`))
      : [];

  if (states.length === 0 && Array.isArray((raw as LegacyCanvasSkill).rectangles)) {
    states = migrateRectanglesToStates(raw as LegacyCanvasSkill);
  }

  const stateIds = new Set(states.map((state) => state.id));
  states = states.map((state) => ({
    ...state,
    transitions: state.transitions.filter((transition) => stateIds.has(transition.to)),
  }));

  const preferredInitial = flattened?.initial ?? raw.initial;
  const initial =
    preferredInitial && stateIds.has(preferredInitial)
      ? preferredInitial
      : (states[0]?.id ?? null);

  return {
    id: raw.id || createId(),
    name: raw.name?.trim() || "Skill",
    description: raw.description ?? "",
    version: raw.version?.trim() || "0.1.0",
    createdAt: raw.createdAt || new Date().toISOString(),
    updatedAt: raw.updatedAt || new Date().toISOString(),
    initial,
    params: Array.isArray(raw.params)
      ? raw.params
          .map((param) => ({
            name: String(param.name || "").trim(),
            type: String(param.type || "string").trim() || "string",
            required: Boolean(param.required),
          }))
          .filter((param) => param.name)
      : [],
    states,
    viewport: raw.viewport ?? { panX: 0, panY: 0, zoom: 1 },
    flowDirection: raw.flowDirection === "horizontal" ? "horizontal" : "vertical",
  };
}

export function skillToEditorState(skill: Skill): FsmEditorState {
  return {
    initial: skill.initial,
    params: skill.params.map((param) => ({ ...param })),
    states: skill.states.map((state) => ({
      ...state,
      onEnter: [...state.onEnter],
      transitions: state.transitions.map((transition) => ({
        ...transition,
        actions: [...transition.actions],
        waypoints: transition.waypoints?.map((point) => ({ ...point })),
      })),
    })),
    viewport: { ...skill.viewport },
    flowDirection: skill.flowDirection ?? "vertical",
  };
}

export function suggestStateDropPosition(states: FsmState[]): { x: number; y: number } {
  const col = states.length % 4;
  const row = Math.floor(states.length / 4);
  return {
    x: GRID_SIZE * 2 + col * (DEFAULT_STATE_WIDTH + GRID_SIZE * 2),
    y: GRID_SIZE * 2 + row * (DEFAULT_STATE_HEIGHT + GRID_SIZE * 3),
  };
}
