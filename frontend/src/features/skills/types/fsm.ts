export const GRID_SIZE = 20;
export const MIN_STATE_SIZE = GRID_SIZE * 4;
export const DEFAULT_STATE_WIDTH = GRID_SIZE * 8;
export const DEFAULT_STATE_HEIGHT = GRID_SIZE * 4;

export type CanvasTool = "select" | "state" | "transition";

export interface Point {
  x: number;
  y: number;
}

export interface Viewport {
  panX: number;
  panY: number;
  zoom: number;
}

export interface DraftRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SkillParam {
  name: string;
  type: string;
  required: boolean;
}

export type ResizeHandle = "nw" | "n" | "ne" | "e" | "se" | "s" | "sw" | "w";

export const RESIZE_HANDLES: ResizeHandle[] = [
  "nw",
  "n",
  "ne",
  "e",
  "se",
  "s",
  "sw",
  "w",
];

export type RectSide = "top" | "right" | "bottom" | "left";

export interface FsmTransition {
  id: string;
  event: string;
  guard: string;
  actions: string[];
  to: string;
  /** Optional anchor side on the source state border. */
  fromSide?: RectSide;
  /** Optional anchor side on the target state border. */
  toSide?: RectSide;
  /** Position along the source edge (0–1). */
  fromAnchor?: number;
  /** Position along the target edge (0–1). */
  toAnchor?: number;
  originNodeId?: string;
  originEdgeId?: string;
}

export interface FsmState {
  id: string;
  /** Human-readable label on the canvas; runtime uses `id`. */
  name?: string;
  onEnter: string[];
  final: boolean;
  transitions: FsmTransition[];
  x: number;
  y: number;
  width: number;
  height: number;
  originNodeId?: string;
}

export interface FsmEditorState {
  initial: string | null;
  params: SkillParam[];
  states: FsmState[];
  viewport: Viewport;
}

/** Selection in the FSM canvas editor. */
export type FsmSelection =
  | { kind: "state"; stateId: string }
  | { kind: "transition"; stateId: string; transitionId: string }
  | null;
