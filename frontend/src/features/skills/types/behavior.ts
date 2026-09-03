import type { Viewport } from "@/features/skills/types/fsm";

export const BEHAVIOR_GRAPH_VERSION = 1;
export const BEHAVIOR_COMPILER_VERSION = "1";

export type LayoutRect = {
  x: number;
  y: number;
  width?: number;
  height?: number;
};

export type NodeLayout = {
  story?: LayoutRect;
  logic?: LayoutRect;
};

export type Explanation = {
  what?: string;
  why?: string;
  when?: string;
  until?: string;
  result?: string;
};

export type WaitFor =
  | { type: "event"; event: string }
  | { type: "action"; actionId: string }
  | { type: "input"; event?: string }
  | { type: "condition"; event: string; expression: string };

export type NodeBase = {
  id: string;
  title: string;
  explanation?: Explanation;
  layout?: NodeLayout;
};

export type WaitNode = NodeBase & {
  type: "wait";
  waitFor: WaitFor;
};

export type DoNode = NodeBase & {
  type: "do";
  actionId: string;
};

export type DecideBranch = {
  id: string;
  label: string;
  guard: string;
  to: string;
};

export type DecideNode = NodeBase & {
  type: "decide";
  question: string;
  branches: DecideBranch[];
};

export type EndNode = NodeBase & {
  type: "end";
};

export type BehaviorNode = WaitNode | DoNode | DecideNode | EndNode;

export type BehaviorEdge = {
  id: string;
  from: string;
  to: string;
  kind: "next" | "loop";
};

export type BehaviorGraph = {
  version: number;
  entry: string;
  nodes: BehaviorNode[];
  edges: BehaviorEdge[];
};

export type CompiledTransition = {
  id: string;
  event: string;
  guard: string;
  actions: string[];
  to: string;
  originNodeId: string;
  originEdgeId: string;
};

export type CompiledState = {
  id: string;
  name?: string;
  originNodeId: string;
  onEnter: string[];
  final: boolean;
  transitions: CompiledTransition[];
  x: number;
  y: number;
  width: number;
  height: number;
};

export type ExecutionArtifact = {
  compilerVersion: string;
  compiledAt?: string;
  initial: string;
  states: CompiledState[];
};

export type CompileResult =
  | { ok: true; errors: BehaviorIssue[]; artifact: ExecutionArtifact }
  | { ok: false; errors: BehaviorIssue[]; artifact: null };

export type BehaviorIssue = {
  code: string;
  severity: "error" | "warning";
  message: string;
  nodeId?: string | null;
};

export type BehaviorSelection =
  | { kind: "node"; nodeId: string }
  | { kind: "edge"; edgeId: string }
  | { kind: "branch"; nodeId: string; branchId: string }
  | null;

export type CanvasMode = "story" | "logic" | "runtime";

export type BehaviorTool = "select" | "wait" | "do" | "decide" | "end" | "connect";

export type BehaviorEditorState = {
  behavior: BehaviorGraph;
  params: { name: string; type: string; required: boolean }[];
  storyViewport: Viewport;
  logicViewport: Viewport;
};

export const DEFAULT_NODE_SIZE = { width: 280, height: 96 };

export function emptyBehaviorGraph(): BehaviorGraph {
  return { version: BEHAVIOR_GRAPH_VERSION, entry: "", nodes: [], edges: [] };
}

export function emptyBehaviorEditorState(): BehaviorEditorState {
  return {
    behavior: emptyBehaviorGraph(),
    params: [],
    storyViewport: { panX: 0, panY: 0, zoom: 1 },
    logicViewport: { panX: 0, panY: 0, zoom: 1 },
  };
}
