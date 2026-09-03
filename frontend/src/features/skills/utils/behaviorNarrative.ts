import type { BehaviorGraph } from "@/features/skills/types/behavior";
import { nodeMap, successors } from "@/features/skills/utils/behaviorGraph";

export function behaviorNarrative(graph: BehaviorGraph | null | undefined): string {
  if (!graph) return "";
  const source = graph;
  const nodes = nodeMap(graph);
  const entry = graph.entry || "";
  if (!entry || !nodes.has(entry)) return "";
  const lines: string[] = [];
  const seen = new Set<string>();

  function titleOf(nodeId: string): string {
    const node = nodes.get(nodeId);
    if (!node) return nodeId;
    const raw = node.type === "decide" ? node.question || node.title : node.title;
    return (raw || nodeId).replace(/\.+$/, "");
  }

  function walk(nodeId: string) {
    if (seen.has(nodeId)) {
      lines.push(`Возвращаюсь к «${titleOf(nodeId)}».`);
      return;
    }
    seen.add(nodeId);
    const node = nodes.get(nodeId);
    if (!node) return;
    if (node.type === "wait") {
      lines.push(`Когда ${titleOf(nodeId)}.`);
    } else if (node.type === "do") {
      lines.push(`Я ${titleOf(nodeId)}.`);
    } else if (node.type === "decide") {
      const question = (node.question || "Что дальше?").replace(/\?+$/, "");
      lines.push(`${question}?`);
      for (const branch of node.branches) {
        lines.push(`Если ${branch.label || "ветка"}:`);
        if (branch.to) walk(branch.to);
      }
      return;
    } else if (node.type === "end") {
      lines.push("Задача завершена.");
      return;
    }
    for (const { item } of successors(source, nodeId)) {
      if (item.to) walk(item.to);
    }
  }

  walk(entry);
  return lines.join(" ");
}
