import type { FsmState } from "@/features/skills/types/fsm";
import { GRID_SIZE, MIN_STATE_SIZE } from "@/features/skills/types/fsm";
import { MIN_NODE_GAP, type FlowDirection } from "@/features/skills/utils/geometry/config";
import { snap } from "@/features/skills/utils/canvasGeometry";

const LAYER_GAP = Math.max(MIN_NODE_GAP * 2, GRID_SIZE * 4);

export function autoLayoutStates(
  states: FsmState[],
  initial: string | null,
  direction: FlowDirection = "vertical",
): FsmState[] {
  if (states.length === 0) return [];

  const byId = new Map(states.map((state) => [state.id, state]));
  const outgoing = new Map<string, string[]>();
  for (const state of states) {
    outgoing.set(
      state.id,
      state.transitions.map((transition) => transition.to).filter((id) => byId.has(id)),
    );
  }

  const backEdges = new Set<string>();
  const stack = new Set<string>();
  const seen = new Set<string>();

  function dfs(nodeId: string) {
    seen.add(nodeId);
    stack.add(nodeId);
    for (const next of outgoing.get(nodeId) ?? []) {
      if (!seen.has(next)) dfs(next);
      else if (stack.has(next)) backEdges.add(`${nodeId}->${next}`);
    }
    stack.delete(nodeId);
  }

  const start = initial && byId.has(initial) ? initial : states[0].id;
  dfs(start);
  for (const state of states) {
    if (!seen.has(state.id)) dfs(state.id);
  }

  const rank = new Map<string, number>();
  rank.set(start, 0);
  const queue = [start];
  const queued = new Set(queue);
  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    const current = rank.get(nodeId) ?? 0;
    for (const next of outgoing.get(nodeId) ?? []) {
      if (backEdges.has(`${nodeId}->${next}`)) continue;
      const nextRank = Math.max(rank.get(next) ?? 0, current + 1);
      rank.set(next, nextRank);
      if (!queued.has(next)) {
        queued.add(next);
        queue.push(next);
      }
    }
  }

  let maxRank = 0;
  for (const value of rank.values()) maxRank = Math.max(maxRank, value);
  for (const state of states) {
    if (!rank.has(state.id)) {
      maxRank += 1;
      rank.set(state.id, maxRank);
    }
  }

  const layers = new Map<number, FsmState[]>();
  for (const state of states) {
    const layer = rank.get(state.id) ?? 0;
    const list = layers.get(layer) ?? [];
    list.push(state);
    layers.set(layer, list);
  }

  const next = states.map((state) => ({
    ...state,
    onEnter: [...state.onEnter],
    transitions: state.transitions.map((transition) => ({
      ...transition,
      actions: [...transition.actions],
      waypoints: transition.waypoints?.map((point) => ({ ...point })),
    })),
  }));
  const nextById = new Map(next.map((state) => [state.id, state]));

  const orderedRanks = [...layers.keys()].sort((left, right) => left - right);
  let cursor = GRID_SIZE * 2;

  for (const layerIndex of orderedRanks) {
    const layer = (layers.get(layerIndex) ?? []).map((state) => nextById.get(state.id)!);
    layer.sort((left, right) => (direction === "vertical" ? left.x - right.x : left.y - right.y));
    const layerDepth = Math.max(...layer.map((state) => (direction === "vertical" ? state.height : state.width)), MIN_STATE_SIZE);
    let along = GRID_SIZE * 2;
    for (const state of layer) {
      if (direction === "vertical") {
        state.x = snap(along);
        state.y = snap(cursor);
        along += state.width + LAYER_GAP;
      } else {
        state.x = snap(cursor);
        state.y = snap(along);
        along += state.height + LAYER_GAP;
      }
    }
    cursor += layerDepth + LAYER_GAP;
  }

  return next;
}
