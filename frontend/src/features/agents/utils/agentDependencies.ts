import type { ActionDef, Agent, Skill } from "@/features/agents/types/agent";
import { getToolDefinition, isToolImplemented } from "@/features/tools/registry/builtinTools";
import {
  enabledInstances,
  resolveRecipeTool,
  type ResolveToolStatus,
} from "@/features/tools/utils/resolveToolInstance";

export type ToolDependencyStatus = ResolveToolStatus | "unimplemented";

/** One recipe step: which tool instance and command an action calls. */
export interface ActionCommandUse {
  stepId: string;
  command: string;
  instanceId: string;
  typeId: string;
  status: ToolDependencyStatus;
}

export interface SkillActionDependency {
  actionId: string;
  /** `null` — the skill references an action the agent does not have. */
  action: ActionDef | null;
  commands: ActionCommandUse[];
}

export interface SkillToolDependency {
  /** Resolved instance id; the raw recipe reference when it does not resolve. */
  instanceId: string;
  typeId: string;
  name: string;
  world: boolean;
  status: ToolDependencyStatus;
  /** Skill actions that call this tool. */
  actionIds: string[];
  /** Tool-declared events the skill's transitions wait for. */
  events: string[];
}

export interface SkillDependencies {
  actions: SkillActionDependency[];
  /** World tools (left zone of the constructor). */
  channels: SkillToolDependency[];
  /** Non-world tools (bottom zone of the constructor). */
  plugins: SkillToolDependency[];
}

/** Channels are matched by type (one enabled instance per world type), plugins by instance. */
export type ToolTarget =
  | { kind: "type"; typeId: string }
  | { kind: "instance"; instanceId: string };

export interface ToolUsage {
  actions: Array<{ action: ActionDef; commands: string[] }>;
  skills: Array<{ skill: Skill; actionIds: string[]; events: string[] }>;
}

function pushUnique(list: string[], value: string) {
  if (value && !list.includes(value)) list.push(value);
}

function matchesTarget(entry: { instanceId: string; typeId: string }, target: ToolTarget): boolean {
  return target.kind === "type"
    ? entry.typeId === target.typeId
    : entry.instanceId === target.instanceId;
}

/** Action ids in order of first reference: states top to bottom, `onEnter` before transitions. */
export function skillActionIds(skill: Skill): string[] {
  const ids: string[] = [];
  for (const state of skill.states) {
    for (const actionId of state.onEnter) pushUnique(ids, actionId);
    for (const transition of state.transitions) {
      for (const actionId of transition.actions) pushUnique(ids, actionId);
    }
  }
  return ids;
}

export function actionCommandUses(agent: Agent, action: ActionDef): ActionCommandUse[] {
  return action.recipe.map((step) => {
    const resolved = resolveRecipeTool(agent, step.tool);
    const def = resolved.typeId ? getToolDefinition(resolved.typeId) : undefined;
    let status: ToolDependencyStatus = resolved.status;
    if (!def) status = "unknown";
    else if (status === "ok" && !isToolImplemented(def)) status = "unimplemented";
    return {
      stepId: step.id,
      command: step.command,
      instanceId: resolved.instanceId,
      typeId: resolved.typeId,
      status,
    };
  });
}

function listenedEvents(skill: Skill): Set<string> {
  const events = new Set<string>();
  for (const state of skill.states) {
    for (const transition of state.transitions) {
      const event = transition.event?.trim();
      if (event) events.add(event);
    }
  }
  return events;
}

export function skillDependencies(agent: Agent, skill: Skill): SkillDependencies {
  const actionsById = new Map(agent.actions.map((action) => [action.id, action]));
  const tools = new Map<string, SkillToolDependency>();

  function toolEntry(instanceId: string, typeId: string, status: ToolDependencyStatus) {
    const key = instanceId || typeId;
    let entry = tools.get(key);
    if (!entry) {
      const def = typeId ? getToolDefinition(typeId) : undefined;
      const instance = agent.tools.find((item) => item.id === instanceId);
      entry = {
        instanceId,
        typeId,
        // The table labels channels by type and plugins by instance.
        name: def?.world ? def.name : (instance?.name ?? def?.name ?? (typeId || instanceId)),
        world: Boolean(def?.world),
        status,
        actionIds: [],
        events: [],
      };
      tools.set(key, entry);
    }
    return entry;
  }

  const actions = skillActionIds(skill).map((actionId): SkillActionDependency => {
    const action = actionsById.get(actionId) ?? null;
    const commands = action ? actionCommandUses(agent, action) : [];
    for (const use of commands) {
      if (!use.instanceId && !use.typeId) continue;
      pushUnique(toolEntry(use.instanceId, use.typeId, use.status).actionIds, actionId);
    }
    return { actionId, action, commands };
  });

  const events = listenedEvents(skill);
  if (events.size > 0) {
    for (const instance of enabledInstances(agent)) {
      const def = getToolDefinition(instance.toolId);
      if (!def) continue;
      for (const event of def.events) {
        if (!events.has(event.id)) continue;
        const status = isToolImplemented(def) ? "ok" : "unimplemented";
        pushUnique(toolEntry(instance.id, instance.toolId, status).events, event.id);
      }
    }
  }

  const entries = [...tools.values()];
  return {
    actions,
    channels: entries.filter((entry) => entry.world),
    plugins: entries.filter((entry) => !entry.world),
  };
}

export function toolUsage(agent: Agent, target: ToolTarget): ToolUsage {
  const actions: ToolUsage["actions"] = [];
  for (const action of agent.actions) {
    const commands: string[] = [];
    for (const use of actionCommandUses(agent, action)) {
      if (matchesTarget(use, target)) pushUnique(commands, use.command);
    }
    if (commands.length > 0) actions.push({ action, commands });
  }

  const skills: ToolUsage["skills"] = [];
  for (const skill of agent.skills) {
    const deps = skillDependencies(agent, skill);
    const actionIds: string[] = [];
    const events: string[] = [];
    for (const entry of [...deps.channels, ...deps.plugins]) {
      if (!matchesTarget(entry, target)) continue;
      entry.actionIds.forEach((id) => pushUnique(actionIds, id));
      entry.events.forEach((id) => pushUnique(events, id));
    }
    if (actionIds.length > 0 || events.length > 0) skills.push({ skill, actionIds, events });
  }

  return { actions, skills };
}
