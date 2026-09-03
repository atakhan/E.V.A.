import type { BehaviorGraph, BehaviorIssue } from "@/features/skills/types/behavior";
import { nodeMap, outgoingEdges, successors } from "@/features/skills/utils/behaviorGraph";

export function validateBehaviorGraph(
  graph: BehaviorGraph | null | undefined,
  options?: { actionIds?: Set<string> },
): BehaviorIssue[] {
  const issues: BehaviorIssue[] = [];
  if (!graph) return issues;
  const nodesById = nodeMap(graph);
  const known = new Set(nodesById.keys());
  const entry = graph.entry || "";

  if (graph.nodes.length === 0) {
    issues.push({
      code: "behavior_empty",
      severity: "warning",
      message: "Behavior Graph пуст",
    });
    return issues;
  }

  if (entry && !known.has(entry)) {
    issues.push({
      code: "invalid_entry",
      severity: "error",
      message: `entry «${entry}» не найден среди узлов`,
      nodeId: entry,
    });
  } else if (entry && nodesById.get(entry)?.type !== "wait") {
    issues.push({
      code: "entry_not_wait",
      severity: "error",
      message: "entry в v1 должен быть wait",
      nodeId: entry,
    });
  }

  for (const edge of graph.edges) {
    if (!known.has(edge.from)) {
      issues.push({
        code: "dangling_edge_from",
        severity: "error",
        message: `ребро ${edge.id}: неизвестный from`,
        nodeId: edge.from,
      });
    }
    if (!known.has(edge.to)) {
      issues.push({
        code: "dangling_edge_to",
        severity: "error",
        message: `ребро ${edge.id}: неизвестный to`,
        nodeId: edge.to,
      });
    }
  }

  const actionIds = options?.actionIds;

  for (const node of graph.nodes) {
    if (node.type === "do" && !node.actionId.trim()) {
      issues.push({
        code: "do_missing_action",
        severity: "error",
        message: `${node.id}: do без actionId`,
        nodeId: node.id,
      });
    }
    if (node.type === "do" && actionIds && node.actionId && !actionIds.has(node.actionId)) {
      issues.push({
        code: "unknown_action",
        severity: "error",
        message: `${node.id}: неизвестный action «${node.actionId}»`,
        nodeId: node.id,
      });
    }
    if (node.type === "wait") {
      const waitFor = node.waitFor;
      if (waitFor.type === "event" && !waitFor.event.trim()) {
        issues.push({
          code: "wait_missing_event",
          severity: "error",
          message: `${node.id}: wait.event без event`,
          nodeId: node.id,
        });
      }
      if (waitFor.type === "action" && !waitFor.actionId.trim()) {
        issues.push({
          code: "wait_missing_action",
          severity: "error",
          message: `${node.id}: wait.action без actionId`,
          nodeId: node.id,
        });
      }
      if (waitFor.type === "condition" && !waitFor.event.trim()) {
        issues.push({
          code: "wait_missing_event",
          severity: "error",
          message: `${node.id}: wait.condition без event`,
          nodeId: node.id,
        });
      }
      if (outgoingEdges(graph, node.id).length > 1) {
        issues.push({
          code: "wait_multiple_next",
          severity: "error",
          message: `${node.id}: wait может иметь одно исходящее ребро`,
          nodeId: node.id,
        });
      }
    }
    if (node.type === "do" && outgoingEdges(graph, node.id).length > 1) {
      issues.push({
        code: "do_multiple_next",
        severity: "error",
        message: `${node.id}: do может иметь одно исходящее ребро`,
        nodeId: node.id,
      });
    }
    if (node.type === "end" && outgoingEdges(graph, node.id).length > 0) {
      issues.push({
        code: "end_has_outgoing",
        severity: "error",
        message: `${node.id}: end не должен иметь исходящих рёбер`,
        nodeId: node.id,
      });
    }
    if (node.type === "decide") {
      if (node.branches.length === 0) {
        issues.push({
          code: "decide_no_branches",
          severity: "error",
          message: `${node.id}: decide без веток`,
          nodeId: node.id,
        });
      }
      for (const branch of node.branches) {
        if (!known.has(branch.to)) {
          issues.push({
            code: "dangling_branch",
            severity: "error",
            message: `${node.id}: ветка на неизвестный узел`,
            nodeId: node.id,
          });
        } else if (nodesById.get(branch.to)?.type === "decide") {
          issues.push({
            code: "nested_decide",
            severity: "error",
            message: `${node.id}: вложенный decide в v1 запрещён`,
            nodeId: node.id,
          });
        }
      }
    }
    for (const { item } of successors(graph, node.id)) {
      const target = nodesById.get(item.to);
      if (
        node.type === "wait" &&
        node.waitFor.type === "condition" &&
        target?.type === "decide"
      ) {
        issues.push({
          code: "condition_wait_to_decide",
          severity: "error",
          message: `${node.id}: wait.condition не может сразу переходить в decide`,
          nodeId: node.id,
        });
      }
    }
  }

  return issues;
}
