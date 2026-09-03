import type { BehaviorGraph, BehaviorNode, CanvasMode, LayoutRect } from "@/features/skills/types/behavior";
import { DEFAULT_NODE_SIZE } from "@/features/skills/types/behavior";
import { successors } from "@/features/skills/utils/behaviorGraph";

export function nodeRect(node: BehaviorNode, mode: CanvasMode): Required<LayoutRect> {
  const slot = mode === "logic" ? node.layout?.logic : node.layout?.story;
  return {
    x: slot?.x ?? 48,
    y: slot?.y ?? 48,
    width: slot?.width ?? DEFAULT_NODE_SIZE.width,
    height: slot?.height ?? DEFAULT_NODE_SIZE.height,
  };
}

export function withNodeRect(
  node: BehaviorNode,
  mode: CanvasMode,
  rect: LayoutRect,
): BehaviorNode {
  const layout = { ...(node.layout ?? {}) };
  if (mode === "logic") layout.logic = { ...nodeRect(node, mode), ...rect };
  else layout.story = { ...nodeRect(node, "story"), ...rect };
  return { ...node, layout };
}

export function autoLayoutStory(graph: BehaviorGraph): BehaviorGraph {
  const placed = new Set<string>();
  const nodes = graph.nodes.map((node) => ({ ...node }));
  const byId = new Map(nodes.map((node) => [node.id, node]));
  let row = 0;

  function place(nodeId: string) {
    if (placed.has(nodeId)) return;
    placed.add(nodeId);
    const node = byId.get(nodeId);
    if (!node) return;
    node.layout = {
      ...(node.layout ?? {}),
      story: { x: 64, y: 48 + row * 140, width: DEFAULT_NODE_SIZE.width, height: DEFAULT_NODE_SIZE.height },
    };
    row += 1;
    if (node.type === "decide") {
      node.branches.forEach((branch, index) => {
        const child = byId.get(branch.to);
        if (!child || placed.has(child.id)) return;
        child.layout = {
          ...(child.layout ?? {}),
          story: {
            x: 64 + (index === 0 ? -160 : 160),
            y: 48 + row * 140,
            width: DEFAULT_NODE_SIZE.width,
            height: DEFAULT_NODE_SIZE.height,
          },
        };
        placed.add(child.id);
      });
      row += 1;
      for (const branch of node.branches) {
        for (const { item } of successors({ ...graph, nodes }, branch.to)) {
          place(item.to);
        }
      }
      return;
    }
    for (const { item } of successors({ ...graph, nodes }, nodeId)) {
      place(item.to);
    }
  }

  if (graph.entry) place(graph.entry);
  for (const node of nodes) {
    if (!placed.has(node.id)) place(node.id);
  }
  return { ...graph, nodes };
}

export function autoLayoutLogic(graph: BehaviorGraph): BehaviorGraph {
  const placed = new Set<string>();
  const nodes = graph.nodes.map((node) => ({ ...node }));
  const byId = new Map(nodes.map((node) => [node.id, node]));
  let row = 0;

  function place(nodeId: string, column: number) {
    if (placed.has(nodeId)) return;
    placed.add(nodeId);
    const node = byId.get(nodeId);
    if (!node) return;
    node.layout = {
      ...(node.layout ?? {}),
      logic: {
        x: 48 + column * 300,
        y: 48 + row * 130,
        width: DEFAULT_NODE_SIZE.width,
        height: DEFAULT_NODE_SIZE.height,
      },
    };
    row += 1;
    if (node.type === "decide") {
      const startRow = row;
      node.branches.forEach((branch, index) => {
        row = startRow;
        place(branch.to, column + index);
      });
      return;
    }
    for (const { item } of successors({ ...graph, nodes }, nodeId)) {
      place(item.to, column);
    }
  }

  if (graph.entry) place(graph.entry, 0);
  for (const node of nodes) {
    if (!placed.has(node.id)) place(node.id, 0);
  }
  return { ...graph, nodes };
}

export function fillMissingLayouts(graph: BehaviorGraph): BehaviorGraph {
  if (graph.nodes.every((node) => node.layout?.story && node.layout?.logic)) {
    return graph;
  }
  const storySource = autoLayoutStory(graph);
  const logicSource = autoLayoutLogic(graph);
  const storyById = new Map(storySource.nodes.map((node) => [node.id, node]));
  const logicById = new Map(logicSource.nodes.map((node) => [node.id, node]));
  return {
    ...graph,
    nodes: graph.nodes.map((node) => ({
      ...node,
      layout: {
        story: node.layout?.story ?? storyById.get(node.id)?.layout?.story,
        logic: node.layout?.logic ?? logicById.get(node.id)?.layout?.logic,
      },
    })),
  };
}

export function originNodeIdForRunState(
  currentState: string,
  graph: BehaviorGraph,
  compiledStates?: Array<{ id: string; originNodeId: string }>,
): string | null {
  const compiled = compiledStates?.find((state) => state.id === currentState);
  if (compiled) return compiled.originNodeId;
  const waitGuess = `node_wait_${currentState.replace(/[^A-Za-z0-9_]+/g, "_")}`;
  if (graph.nodes.some((node) => node.id === waitGuess)) return waitGuess;
  const doMatch = graph.nodes.find((node) => node.type === "do" && `s_${node.id.replace(/[^A-Za-z0-9_]+/g, "_")}` === currentState);
  return doMatch?.id ?? null;
}
