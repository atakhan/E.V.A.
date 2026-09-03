import type { AgentIssue, AgentIssueSeverity } from "@/features/agents/utils/validateAgent";
import type { BehaviorSelection } from "@/features/skills/types/behavior";
import type { FsmSelection } from "@/features/skills/types/fsm";

export interface SkillIssueMaps {
  skillLevel: AgentIssue[];
  byState: Map<string, AgentIssue[]>;
  byTransition: Map<string, AgentIssue[]>;
  byNode: Map<string, AgentIssue[]>;
}

export function transitionIssueKey(stateId: string, transitionId: string): string {
  return `${stateId}:${transitionId}`;
}

export function buildSkillIssueMaps(issues: AgentIssue[]): SkillIssueMaps {
  const skillLevel: AgentIssue[] = [];
  const byState = new Map<string, AgentIssue[]>();
  const byTransition = new Map<string, AgentIssue[]>();
  const byNode = new Map<string, AgentIssue[]>();

  for (const issue of issues) {
    const locator = issue.locator;
    if (!locator || locator.kind === "skill") {
      skillLevel.push(issue);
      continue;
    }
    if (locator.kind === "node") {
      const list = byNode.get(locator.nodeId) ?? [];
      list.push(issue);
      byNode.set(locator.nodeId, list);
      continue;
    }
    if (locator.kind === "state") {
      const list = byState.get(locator.stateId) ?? [];
      list.push(issue);
      byState.set(locator.stateId, list);
      continue;
    }
    if (locator.kind === "transition") {
      const key = transitionIssueKey(locator.stateId, locator.transitionId);
      const list = byTransition.get(key) ?? [];
      list.push(issue);
      byTransition.set(key, list);
      continue;
    }
    skillLevel.push(issue);
  }

  return { skillLevel, byState, byTransition, byNode };
}

const SEVERITY_RANK: Record<AgentIssueSeverity, number> = {
  error: 3,
  warning: 2,
  info: 1,
};

export function worstSeverity(issues: AgentIssue[]): AgentIssueSeverity | null {
  if (issues.length === 0) return null;
  return issues.reduce<AgentIssueSeverity>(
    (worst, issue) => (SEVERITY_RANK[issue.severity] > SEVERITY_RANK[worst] ? issue.severity : worst),
    "info",
  );
}

export function countBySeverity(issues: AgentIssue[]): {
  errors: number;
  warnings: number;
  infos: number;
} {
  return {
    errors: issues.filter((issue) => issue.severity === "error").length,
    warnings: issues.filter((issue) => issue.severity === "warning").length,
    infos: issues.filter((issue) => issue.severity === "info").length,
  };
}

export function filterIssuesForSelection(
  issues: AgentIssue[],
  selection: FsmSelection | BehaviorSelection,
): AgentIssue[] {
  if (!selection) return issues;
  if (selection.kind === "node" || selection.kind === "branch") {
    return issues.filter(
      (issue) =>
        issue.locator?.kind === "skill" ||
        (issue.locator?.kind === "node" && issue.locator.nodeId === selection.nodeId),
    );
  }
  if (selection.kind === "edge") {
    return issues.filter((issue) => issue.locator?.kind === "skill");
  }
  if (selection.kind === "state") {
    return issues.filter(
      (issue) =>
        issue.locator?.kind === "skill" ||
        (issue.locator?.kind === "state" && issue.locator.stateId === selection.stateId) ||
        (issue.locator?.kind === "transition" && issue.locator.stateId === selection.stateId),
    );
  }
  const key = transitionIssueKey(selection.stateId, selection.transitionId);
  return issues.filter(
    (issue) =>
      issue.locator?.kind === "skill" ||
      (issue.locator?.kind === "transition" &&
        transitionIssueKey(issue.locator.stateId, issue.locator.transitionId) === key),
  );
}
