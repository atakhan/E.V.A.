import type {
  BehaviorEdge,
  BehaviorGraph,
  BehaviorNode,
  WaitFor,
} from "@/features/skills/types/behavior";
import { EVENT_TITLES } from "@/features/skills/utils/skillEvents";
import { createId } from "@/shared/utils/id";

export function sanitizeId(raw: string): string {
  const value = raw.trim().replace(/[^A-Za-z0-9_]+/g, "_");
  return value || "x";
}

export function fsmStateId(nodeId: string): string {
  return `s_${sanitizeId(nodeId)}`;
}

export function fsmTransitionId(originId: string): string {
  return `t_${sanitizeId(originId)}`;
}

export function waitNodeId(stateId: string): string {
  return `node_wait_${sanitizeId(stateId)}`;
}

export function doNodeId(transitionId: string, actionId: string): string {
  return `node_do_${sanitizeId(transitionId)}_${sanitizeId(actionId)}`;
}

export function decideNodeId(stateId: string, event: string): string {
  return `node_decide_${sanitizeId(stateId)}_${sanitizeId(event)}`;
}

export function endNodeId(stateId: string): string {
  return `node_end_${sanitizeId(stateId)}`;
}

export function edgeId(fromId: string, toId: string, index: number): string {
  return `edge_${sanitizeId(fromId)}_${sanitizeId(toId)}_${index}`;
}

export function branchId(transitionId: string, index: number): string {
  return `branch_${sanitizeId(transitionId || String(index))}_${index}`;
}

export { EVENT_TITLES };

export function nodeMap(graph: BehaviorGraph): Map<string, BehaviorNode> {
  return new Map(graph.nodes.map((node) => [node.id, node]));
}

export function outgoingEdges(graph: BehaviorGraph, nodeId: string): BehaviorEdge[] {
  return graph.edges.filter((edge) => edge.from === nodeId).sort((a, b) => a.id.localeCompare(b.id));
}

export function successors(
  graph: BehaviorGraph,
  nodeId: string,
): Array<{ kind: "edge" | "branch"; item: { id: string; to: string; guard?: string } }> {
  const node = nodeMap(graph).get(nodeId);
  if (!node) return [];
  if (node.type === "decide") {
    return node.branches.map((branch) => ({
      kind: "branch" as const,
      item: { id: branch.id, to: branch.to, guard: branch.guard },
    }));
  }
  return outgoingEdges(graph, nodeId).map((edge) => ({
    kind: "edge" as const,
    item: { id: edge.id, to: edge.to },
  }));
}

export function actionIdFromCompletedEvent(event: string): string | null {
  const prefix = "action.";
  const suffix = ".completed";
  if (event.startsWith(prefix) && event.endsWith(suffix)) {
    const middle = event.slice(prefix.length, event.length - suffix.length);
    return middle || null;
  }
  return null;
}

export function waitEventAndGuard(node: Extract<BehaviorNode, { type: "wait" }>): {
  event: string;
  guard: string;
} {
  const waitFor = node.waitFor;
  if (waitFor.type === "event") return { event: waitFor.event || "event", guard: "" };
  if (waitFor.type === "action") {
    return { event: `action.${waitFor.actionId}.completed`, guard: "" };
  }
  if (waitFor.type === "input") {
    return { event: waitFor.event || "channel.message.received", guard: "" };
  }
  return { event: waitFor.event || "event", guard: waitFor.expression || "" };
}

export function leavingEvent(node: BehaviorNode): { event: string; guard: string } | null {
  if (node.type === "wait") return waitEventAndGuard(node);
  if (node.type === "do") return { event: `action.${node.actionId}.completed`, guard: "" };
  return null;
}

export function defaultWaitTitle(waitFor: WaitFor): string {
  if (waitFor.type === "event") {
    return EVENT_TITLES[waitFor.event] ?? waitFor.event ?? "Когда случается событие";
  }
  if (waitFor.type === "action") return `Жду завершения «${waitFor.actionId}»`;
  if (waitFor.type === "input") {
    const event = waitFor.event || "channel.message.received";
    return EVENT_TITLES[event] ?? "Жду ответа";
  }
  return "Жду, пока выполнится условие";
}

export function normalizeGuard(guard: string | undefined | null): string {
  return (guard || "").trim().split(/\s+/).join(" ");
}

export function skillHasBehavior(behavior: BehaviorGraph | undefined | null): boolean {
  return Boolean(behavior && behavior.nodes.length > 0);
}

export function lastOpenNodeId(graph: BehaviorGraph): string | null {
  if (!graph.entry) {
    const candidate = [...graph.nodes].reverse().find((node) => node.type !== "end");
    return candidate?.id ?? null;
  }
  const nodes = nodeMap(graph);
  const seen = new Set<string>();
  let current: string | null = graph.entry;
  let last: string | null = current;
  while (current && !seen.has(current)) {
    seen.add(current);
    const node = nodes.get(current);
    if (!node || node.type === "end") break;
    last = current;
    const nexts = successors(graph, current);
    if (nexts.length !== 1) break;
    current = nexts[0]?.item.to ?? null;
  }
  return last;
}

export function insertBehaviorStep(
  graph: BehaviorGraph,
  node: BehaviorNode,
  fromId: string | null,
  makeId: () => string = createId,
): BehaviorGraph {
  const entry = graph.entry || (node.type === "wait" ? node.id : graph.entry);
  if (!fromId) {
    return { ...graph, entry, nodes: [...graph.nodes, node] };
  }
  const from = graph.nodes.find((item) => item.id === fromId);
  if (!from || from.type === "end") {
    return { ...graph, entry, nodes: [...graph.nodes, node] };
  }

  if (from.type === "decide") {
    const label =
      from.branches.length === 0 ? "Да" : from.branches.length === 1 ? "Нет" : `Ветка ${from.branches.length + 1}`;
    return {
      ...graph,
      entry,
      nodes: [
        ...graph.nodes.map((item) => {
          if (item.id !== fromId || item.type !== "decide") return item;
          return {
            ...item,
            branches: [
              ...item.branches,
              { id: `edge_${makeId()}`, label, guard: "", to: node.id },
            ],
          };
        }),
        node,
      ],
    };
  }

  const existing = graph.edges.find((edge) => edge.from === fromId);
  let nextNode = node;
  if (node.type === "decide" && existing) {
    nextNode = {
      ...node,
      branches: [{ id: `edge_${makeId()}`, label: "Да", guard: "", to: existing.to }],
    };
  }
  const edges = graph.edges.filter((edge) => edge.from !== fromId);
  const kind: BehaviorEdge["kind"] = nextNode.id === entry ? "loop" : "next";
  edges.push({ id: `edge_${makeId()}`, from: fromId, to: nextNode.id, kind });
  if (existing && nextNode.type !== "decide") {
    edges.push({
      id: `edge_${makeId()}`,
      from: nextNode.id,
      to: existing.to,
      kind: existing.kind,
    });
  }
  return { ...graph, entry, nodes: [...graph.nodes, nextNode], edges };
}
