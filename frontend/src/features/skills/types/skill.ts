import type { FsmEditorState, FsmState, FsmTransition, SkillParam } from "@/features/skills/types/fsm";
import type { BehaviorGraph, ExecutionArtifact } from "@/features/skills/types/behavior";
import { emptyBehaviorGraph } from "@/features/skills/types/behavior";
import { liftFsmToBehavior } from "@/features/skills/utils/behaviorLift";
import { skillHasBehavior } from "@/features/skills/utils/behaviorGraph";
import {
  DEFAULT_STATE_HEIGHT,
  DEFAULT_STATE_WIDTH,
  GRID_SIZE,
} from "@/features/skills/types/fsm";
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
  behavior?: BehaviorGraph;
  execution?: ExecutionArtifact;
  storyViewport?: { panX: number; panY: number; zoom: number };
  logicViewport?: { panX: number; panY: number; zoom: number };
}

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
}

export function createEmptyFsmEditorState(): FsmEditorState {
  return {
    initial: null,
    params: [],
    states: [],
    viewport: { panX: 0, panY: 0, zoom: 1 },
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
    behavior: partial?.behavior ?? emptyBehaviorGraph(),
    storyViewport: partial?.storyViewport ?? { panX: 0, panY: 0, zoom: 1 },
    logicViewport: partial?.logicViewport ?? { panX: 0, panY: 0, zoom: 1 },
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

export function skillFromLegacyCanvas(canvas: LegacyCanvasSkill): Skill {
  return normalizeSkill(canvas);
}

export function normalizeSkill(raw: LegacyCanvasSkill | Skill): Skill {
  let states: FsmState[] = Array.isArray(raw.states)
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

  const initial =
    raw.initial && stateIds.has(raw.initial)
      ? raw.initial
      : states[0]?.id ?? null;

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
    behavior: (() => {
      const existing = (raw as Skill).behavior;
      if (skillHasBehavior(existing)) return existing;
      if (states.length > 0) return liftFsmToBehavior(states, initial);
      return existing ?? emptyBehaviorGraph();
    })(),
    execution: (raw as Skill).execution,
    storyViewport: (raw as Skill).storyViewport ?? { panX: 0, panY: 0, zoom: 1 },
    logicViewport: (raw as Skill).logicViewport ?? { panX: 0, panY: 0, zoom: 1 },
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
      })),
    })),
    viewport: { ...skill.viewport },
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
