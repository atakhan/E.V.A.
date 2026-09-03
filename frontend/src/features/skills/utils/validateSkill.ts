import type {
  AgentIssue,
  AgentIssueSeverity,
  SkillIssueLocator,
} from "@/features/agents/utils/validateAgent";
import type { Skill } from "@/features/skills/types/skill";
import { compileBehavior } from "@/features/skills/utils/behaviorCompile";
import { skillHasBehavior } from "@/features/skills/utils/behaviorGraph";
import { validateBehaviorGraph } from "@/features/skills/utils/behaviorValidate";

const SEMVER_PATTERN = /^\d+\.\d+\.\d+$/;
const GUARD_PATTERN = /^[\w.]+\s*(==|!=|>=|<=|>|<)\s*.+$/;

function issue(
  id: string,
  severity: AgentIssueSeverity,
  code: string,
  message: string,
  options?: { href?: string; locator?: SkillIssueLocator; actionId?: string },
): AgentIssue {
  return {
    id,
    severity,
    code,
    message,
    href: options?.href,
    locator: options?.locator,
    actionId: options?.actionId,
  };
}

function reachableStates(skill: Skill): Set<string> {
  const stateIds = new Set(skill.states.map((state) => state.id));
  const initial = skill.initial;
  if (!initial || !stateIds.has(initial)) return new Set();

  const reachable = new Set<string>([initial]);
  const queue = [initial];
  while (queue.length > 0) {
    const current = queue.shift()!;
    const state = skill.states.find((item) => item.id === current);
    if (!state) continue;
    for (const transition of state.transitions) {
      if (stateIds.has(transition.to) && !reachable.has(transition.to)) {
        reachable.add(transition.to);
        queue.push(transition.to);
      }
    }
  }
  return reachable;
}

export function isValidGuardSyntax(guard: string): boolean {
  const expression = guard.trim();
  if (!expression) return true;
  return GUARD_PATTERN.test(expression);
}

export function validateSkill(skill: Skill, actionIds: Set<string>, href?: string): AgentIssue[] {
  const issues: AgentIssue[] = [];
  const skillLocator: SkillIssueLocator = { kind: "skill" };

  if (!SEMVER_PATTERN.test(skill.version)) {
    issues.push(
      issue(
        `skill.${skill.id}.bad-version`,
        "warning",
        "invalid_skill_version",
        `Skill «${skill.name}»: version «${skill.version}» не SemVer (ожидается X.Y.Z)`,
        { href, locator: skillLocator },
      ),
    );
  }

  let working = skill;
  if (skillHasBehavior(skill.behavior)) {
    for (const item of validateBehaviorGraph(skill.behavior, { actionIds })) {
      issues.push(
        issue(
          `skill.${skill.id}.behavior.${item.code}.${item.nodeId ?? "graph"}`,
          item.severity,
          item.code,
          `Skill «${skill.name}»: ${item.message}`,
          { href, locator: item.nodeId ? { kind: "node", nodeId: item.nodeId } : skillLocator },
        ),
      );
    }
    const compiled = compileBehavior(skill.behavior, { actionIds });
    if (compiled.ok) {
      working = {
        ...skill,
        states: compiled.artifact.states,
        initial: compiled.artifact.initial,
      };
    }
  }

  const stateIds = new Set(working.states.map((state) => state.id));
  if (working.states.length === 0) {
    issues.push(
      issue(
        `skill.${skill.id}.empty`,
        "warning",
        "skill_empty",
        `Skill «${skill.name}» без states`,
        { href, locator: skillLocator },
      ),
    );
    return issues;
  }

  if (!working.initial) {
    issues.push(
      issue(
        `skill.${skill.id}.no-initial`,
        "error",
        "missing_initial",
        `Skill «${skill.name}»: не задан initial state`,
        { href, locator: skillLocator },
      ),
    );
  } else if (!stateIds.has(working.initial)) {
    issues.push(
      issue(
        `skill.${skill.id}.bad-initial`,
        "error",
        "invalid_initial",
        `Skill «${skill.name}»: initial «${working.initial}» отсутствует среди states`,
        { href, locator: skillLocator },
      ),
    );
  }

  const reachable = reachableStates(working);
  for (const state of working.states) {
    const stateLocator: SkillIssueLocator = { kind: "state", stateId: state.id };

    if (!reachable.has(state.id) && state.id !== working.initial) {
      issues.push(
        issue(
          `skill.${skill.id}.state.${state.id}.unreachable`,
          "warning",
          "unreachable_state",
          `Skill «${skill.name}» / ${state.id}: state недостижим из initial`,
          { href, locator: stateLocator },
        ),
      );
    }

    if (
      !state.final &&
      state.transitions.length === 0 &&
      state.onEnter.length === 0 &&
      reachable.has(state.id)
    ) {
      issues.push(
        issue(
          `skill.${skill.id}.state.${state.id}.dead-end`,
          "warning",
          "dead_end_state",
          `Skill «${skill.name}» / ${state.id}: не-final state без переходов`,
          { href, locator: stateLocator },
        ),
      );
    }

    for (const actionId of state.onEnter) {
      if (!actionIds.has(actionId)) {
        issues.push(
          issue(
            `skill.${skill.id}.state.${state.id}.on_enter.${actionId}`,
            "error",
            "unknown_action",
            `Skill «${skill.name}» / ${state.id}: on_enter ссылается на неизвестный Action «${actionId}»`,
            { href, locator: stateLocator, actionId },
          ),
        );
      }
    }

    const eventsSeen = new Map<string, string[]>();
    for (const transition of state.transitions) {
      const transitionLocator: SkillIssueLocator = {
        kind: "transition",
        stateId: state.id,
        transitionId: transition.id,
      };

      if (!transition.event.trim()) {
        issues.push(
          issue(
            `skill.${skill.id}.transition.${transition.id}.event`,
            "warning",
            "empty_event",
            `Skill «${skill.name}» / ${state.id}→${transition.to || "?"}: пустой event`,
            { href, locator: transitionLocator },
          ),
        );
      }

      if (transition.guard && !isValidGuardSyntax(transition.guard)) {
        issues.push(
          issue(
            `skill.${skill.id}.transition.${transition.id}.guard`,
            "error",
            "invalid_guard_syntax",
            `Skill «${skill.name}» / ${state.id}: guard «${transition.guard}» синтаксически невалиден`,
            { href, locator: transitionLocator },
          ),
        );
      }

      if (!transition.to || !stateIds.has(transition.to)) {
        issues.push(
          issue(
            `skill.${skill.id}.transition.${transition.id}.to`,
            "error",
            "invalid_transition_target",
            `Skill «${skill.name}» / ${state.id}: переход ведёт в неизвестный state «${transition.to || "—"}»`,
            { href, locator: transitionLocator },
          ),
        );
      }

      for (const actionId of transition.actions) {
        if (!actionIds.has(actionId)) {
          issues.push(
            issue(
              `skill.${skill.id}.transition.${transition.id}.action.${actionId}`,
              "error",
              "unknown_action",
              `Skill «${skill.name}» / ${state.id}: transition ссылается на неизвестный Action «${actionId}»`,
              { href, locator: transitionLocator, actionId },
            ),
          );
        }
      }

      const event = transition.event.trim();
      if (event) {
        const key = `${state.id}:${event}`;
        const guards = eventsSeen.get(key) ?? [];
        guards.push(transition.guard.trim());
        eventsSeen.set(key, guards);
      }
    }

    for (const [key, guards] of eventsSeen.entries()) {
      const emptyGuards = guards.filter((value) => !value);
      if (emptyGuards.length > 1) {
        const eventName = key.split(":")[1] ?? key;
        issues.push(
          issue(
            `skill.${skill.id}.state.${state.id}.event.${eventName}.ambiguous`,
            "warning",
            "ambiguous_guards",
            `Skill «${skill.name}» / ${state.id}: event «${eventName}» имеет несколько handlers без guard`,
            { href, locator: stateLocator },
          ),
        );
      }
    }
  }

  skill.params.forEach((param, index) => {
    if (!param.name.trim()) {
      issues.push(
        issue(
          `skill.${skill.id}.param.${index}.empty`,
          "warning",
          "empty_param_name",
          `Skill «${skill.name}»: param без name`,
          { href, locator: { kind: "param", index } },
        ),
      );
    }
  });

  return issues;
}
