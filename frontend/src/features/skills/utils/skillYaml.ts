import type { FsmState, SkillParam } from "@/features/skills/types/fsm";
import type { Skill } from "@/features/skills/types/skill";
import { normalizeSkill } from "@/features/skills/types/skill";
import { createId } from "@/shared/utils/id";

function quoteIfNeeded(value: string): string {
  if (/^[a-zA-Z0-9_./-]+$/.test(value)) return value;
  return JSON.stringify(value);
}

export function skillToYaml(skill: Skill): string {
  const lines: string[] = [
    `id: ${quoteIfNeeded(skill.id)}`,
    `version: ${JSON.stringify(skill.version)}`,
    `description: ${JSON.stringify(skill.description)}`,
    `initial: ${skill.initial ? quoteIfNeeded(skill.initial) : "null"}`,
    "states:",
  ];

  if (skill.states.length === 0) {
    lines.push("  {}");
  } else {
    for (const state of skill.states) {
      lines.push(`  ${state.id}:`);
      lines.push("    on_enter:");
      if (state.onEnter.length === 0) {
        lines.push("      []");
      } else {
        for (const action of state.onEnter) {
          lines.push(`      - ${quoteIfNeeded(action)}`);
        }
      }

      lines.push("    on:");
      if (state.transitions.length === 0) {
        lines.push("      {}");
      } else {
        for (const transition of state.transitions) {
          lines.push(`      ${quoteIfNeeded(transition.event)}:`);
          lines.push("        -");
          if (transition.guard) {
            lines.push(`          guard: ${JSON.stringify(transition.guard)}`);
          }
          lines.push("          actions:");
          if (transition.actions.length === 0) {
            lines.push("            []");
          } else {
            for (const action of transition.actions) {
              lines.push(`            - ${quoteIfNeeded(action)}`);
            }
          }
          lines.push(`          to: ${quoteIfNeeded(transition.to)}`);
        }
      }

      lines.push(`    final: ${state.final ? "true" : "false"}`);
    }
  }

  lines.push("params:");
  if (skill.params.length === 0) {
    lines.push("  []");
  } else {
    for (const param of skill.params) {
      lines.push("  -");
      lines.push(`    name: ${quoteIfNeeded(param.name)}`);
      lines.push(`    required: ${param.required ? "true" : "false"}`);
    }
  }

  return `${lines.join("\n")}\n`;
}

/**
 * Minimal YAML subset parser for Skill FSM (round-trip of our export).
 * Also accepts a JSON object payload.
 */
export function skillFromYaml(raw: string, base: Skill): Skill | { error: string } {
  const trimmed = raw.trim();
  if (!trimmed) return { error: "Пустой YAML" };

  if (trimmed.startsWith("{")) {
    try {
      const parsed = JSON.parse(trimmed) as Partial<Skill>;
      return normalizeSkill({ ...base, ...parsed, id: base.id });
    } catch {
      return { error: "Не удалось разобрать JSON" };
    }
  }

  try {
    const doc = parseSimpleSkillYaml(trimmed);
    return normalizeSkill({
      ...base,
      id: base.id,
      name: base.name,
      description: doc.description ?? base.description,
      version: doc.version ?? base.version,
      initial: doc.initial ?? null,
      params: doc.params ?? [],
      states: mergeLayout(base.states, doc.states ?? []),
      viewport: base.viewport,
      createdAt: base.createdAt,
      updatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Ошибка разбора YAML" };
  }
}

function mergeLayout(existing: FsmState[], imported: FsmState[]): FsmState[] {
  const layoutById = new Map(existing.map((state) => [state.id, state]));
  return imported.map((state, index) => {
    const prev = layoutById.get(state.id);
    if (prev) {
      return {
        ...state,
        x: prev.x,
        y: prev.y,
        width: prev.width,
        height: prev.height,
      };
    }
    return {
      ...state,
      x: 40 + (index % 4) * 200,
      y: 40 + Math.floor(index / 4) * 120,
      width: state.width || 160,
      height: state.height || 80,
    };
  });
}

type YamlDoc = {
  description?: string;
  version?: string;
  initial?: string | null;
  params?: SkillParam[];
  states?: FsmState[];
};

function parseScalar(value: string): string | boolean | null {
  const v = value.trim();
  if (v === "null") return null;
  if (v === "true") return true;
  if (v === "false") return false;
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
    return v.slice(1, -1);
  }
  return v;
}

function parseSimpleSkillYaml(text: string): YamlDoc {
  const lines = text.split(/\r?\n/);
  const doc: YamlDoc = { states: [], params: [] };
  let mode:
    | "root"
    | "states"
    | "state"
    | "on_enter"
    | "on"
    | "event"
    | "event_item"
    | "params"
    | "param_item" = "root";
  let currentState: FsmState | null = null;
  let currentEvent = "";
  let currentParam: SkillParam | null = null;
  let inActions = false;

  for (const rawLine of lines) {
    if (!rawLine.trim() || rawLine.trim().startsWith("#")) continue;
    const indent = rawLine.match(/^ */)?.[0].length ?? 0;
    const line = rawLine.trim();

    if (indent === 0) {
      mode = "root";
      currentState = null;
      currentParam = null;
      inActions = false;
      if (line.startsWith("description:")) {
        doc.description = String(parseScalar(line.slice("description:".length)));
      } else if (line.startsWith("version:")) {
        doc.version = String(parseScalar(line.slice("version:".length)));
      } else if (line.startsWith("initial:")) {
        const value = parseScalar(line.slice("initial:".length));
        doc.initial = value === null ? null : String(value);
      } else if (line.startsWith("states:")) {
        mode = "states";
      } else if (line.startsWith("params:")) {
        mode = "params";
      }
      continue;
    }

    if (mode === "states" && indent === 2 && line.endsWith(":") && line !== "{}:") {
      if (line === "{}") continue;
      const id = line.slice(0, -1).trim();
      currentState = {
        id,
        onEnter: [],
        final: false,
        transitions: [],
        x: 0,
        y: 0,
        width: 160,
        height: 80,
      };
      doc.states!.push(currentState);
      mode = "state";
      continue;
    }

    if (currentState && indent >= 4) {
      if (indent === 4 && line.startsWith("on_enter:")) {
        mode = "on_enter";
        inActions = false;
        continue;
      }
      if (indent === 4 && line.startsWith("on:")) {
        mode = "on";
        inActions = false;
        continue;
      }
      if (indent === 4 && line.startsWith("final:")) {
        currentState.final = parseScalar(line.slice("final:".length)) === true;
        mode = "state";
        continue;
      }
      if (mode === "on_enter" && indent === 6 && line.startsWith("- ")) {
        currentState.onEnter.push(String(parseScalar(line.slice(2))));
        continue;
      }
      if (mode === "on" && indent === 6 && line.endsWith(":")) {
        currentEvent = line.slice(0, -1).trim();
        mode = "event";
        continue;
      }
      if ((mode === "event" || mode === "event_item") && indent === 8 && line === "-") {
        currentState.transitions.push({
          id: createId(),
          event: currentEvent,
          guard: "",
          actions: [],
          to: "",
        });
        mode = "event_item";
        inActions = false;
        continue;
      }
      if (mode === "event_item" && indent >= 10) {
        const transition = currentState.transitions.at(-1);
        if (!transition) continue;
        if (line.startsWith("guard:")) {
          transition.guard = String(parseScalar(line.slice("guard:".length)));
          inActions = false;
        } else if (line.startsWith("actions:")) {
          inActions = true;
        } else if (inActions && line.startsWith("- ")) {
          transition.actions.push(String(parseScalar(line.slice(2))));
        } else if (line.startsWith("to:")) {
          transition.to = String(parseScalar(line.slice("to:".length)));
          inActions = false;
          mode = "event";
        }
        continue;
      }
    }

    if (mode === "params" && indent === 2 && line === "-") {
      currentParam = { name: "", required: false };
      doc.params!.push(currentParam);
      mode = "param_item";
      continue;
    }

    if (mode === "param_item" && currentParam && indent >= 4) {
      if (line.startsWith("name:")) {
        currentParam.name = String(parseScalar(line.slice("name:".length)));
      } else if (line.startsWith("required:")) {
        currentParam.required = parseScalar(line.slice("required:".length)) === true;
      }
    }
  }

  return doc;
}
