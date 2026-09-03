import type {
  BehaviorGraph,
  CompiledState,
  CompileResult,
  ExecutionArtifact,
} from "@/features/skills/types/behavior";
import { BEHAVIOR_COMPILER_VERSION } from "@/features/skills/types/behavior";
import {
  fsmStateId,
  fsmTransitionId,
  leavingEvent,
  nodeMap,
  successors,
} from "@/features/skills/utils/behaviorGraph";
import { validateBehaviorGraph } from "@/features/skills/utils/behaviorValidate";

export function compileBehavior(
  graph: BehaviorGraph | null | undefined,
  options?: { compiledAt?: string; actionIds?: Set<string> },
): CompileResult {
  const errors = validateBehaviorGraph(graph, { actionIds: options?.actionIds });
  const blocking = errors.filter((issue) => issue.severity === "error");
  if (!graph || blocking.length > 0) {
    return { ok: false, errors, artifact: null };
  }

  const nodes = nodeMap(graph);
  const entry = graph.entry || "";
  const ordered = orderedStateNodes(graph, entry);
  const states: CompiledState[] = ordered.map((node, index) => ({
    id: fsmStateId(node.id),
    name: node.title || node.id,
    originNodeId: node.id,
    onEnter: [],
    final: node.type === "end",
    transitions: [],
    x: index * 220,
    y: 0,
    width: 160,
    height: 80,
  }));
  const byOrigin = new Map(states.map((state) => [state.originNodeId, state]));

  for (const node of ordered) {
    if (node.type === "end") continue;
    const leaving = leavingEvent(node);
    if (!leaving) continue;
    for (const { item } of successors(graph, node.id)) {
      emitLeaf(nodes, byOrigin, node.id, leaving.event, leaving.guard, item.id, item.to);
    }
  }

  let initial = "";
  if (entry && byOrigin.has(entry)) {
    initial = byOrigin.get(entry)!.id;
  } else if (states[0]) {
    initial = states[0].id;
  }

  const artifact: ExecutionArtifact = {
    compilerVersion: BEHAVIOR_COMPILER_VERSION,
    initial,
    states,
  };
  if (options?.compiledAt) artifact.compiledAt = options.compiledAt;
  return { ok: true, errors, artifact };
}

function orderedStateNodes(graph: BehaviorGraph, entry: string) {
  const nodes = nodeMap(graph);
  const ordered: Array<NonNullable<ReturnType<typeof nodes.get>>> = [];
  const seen = new Set<string>();
  const queue = entry ? [entry] : [];
  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    if (seen.has(nodeId)) continue;
    seen.add(nodeId);
    const node = nodes.get(nodeId);
    if (!node) continue;
    if (node.type !== "decide") ordered.push(node);
    for (const { item } of successors(graph, nodeId)) {
      if (item.to) queue.push(item.to);
    }
  }
  const leftovers = [...nodes.values()]
    .filter((node) => !seen.has(node.id) && node.type !== "decide")
    .sort((a, b) => a.id.localeCompare(b.id));
  return [...ordered, ...leftovers];
}

function emitLeaf(
  nodes: Map<string, import("@/features/skills/types/behavior").BehaviorNode>,
  byOrigin: Map<string, CompiledState>,
  sourceId: string,
  event: string,
  guard: string,
  originEdgeId: string,
  targetId: string,
) {
  const target = nodes.get(targetId);
  const sourceState = byOrigin.get(sourceId);
  if (!target || !sourceState) return;
  if (target.type === "decide") {
    for (const branch of target.branches) {
      emitLeaf(
        nodes,
        byOrigin,
        sourceId,
        event,
        branch.guard || guard,
        branch.id || originEdgeId,
        branch.to,
      );
    }
    return;
  }
  const actions = target.type === "do" && target.actionId ? [target.actionId] : [];
  sourceState.transitions.push({
    id: fsmTransitionId(originEdgeId),
    event,
    guard: guard || "",
    actions,
    to: fsmStateId(target.id),
    originNodeId: sourceId,
    originEdgeId,
  });
}
