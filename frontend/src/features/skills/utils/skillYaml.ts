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
      if (state.name?.trim()) {
        lines.push(`    name: ${JSON.stringify(state.name.trim())}`);
      }
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
      lines.push(`    type: ${quoteIfNeeded(param.type || "string")}`);
      lines.push(`    required: ${param.required ? "true" : "false"}`);
    }
  }

  return `${lines.join("\n")}\n`;
}

export type YamlDoc = {
  skillId?: string;
  description?: string;
  version?: string;
  initial?: string | null;
  params?: SkillParam[];
  states?: FsmState[];
  warnings?: string[];
};

export function normalizeImportedSkillId(raw: string | undefined, fallback: string): string {
  const value = (raw ?? fallback).trim();
  const withoutPrefix = value.startsWith("skill.") ? value.slice("skill.".length) : value;
  return withoutPrefix.replace(/[^a-zA-Z0-9_./-]+/g, "_").slice(0, 64) || fallback;
}

export function parseSkillYamlDocument(raw: string): YamlDoc | { error: string } {
  const trimmed = raw.trim();
  if (!trimmed) return { error: "Пустой YAML" };

  if (trimmed.startsWith("{")) {
    try {
      const parsed = JSON.parse(trimmed) as Partial<Skill> & { id?: string };
      return {
        skillId: parsed.id,
        description: parsed.description,
        version: parsed.version,
        initial: parsed.initial ?? null,
        params: parsed.params ?? [],
        states: parsed.states ?? [],
        warnings: [],
      };
    } catch {
      return { error: "Не удалось разобрать JSON" };
    }
  }

  try {
    return parseSimpleSkillYaml(trimmed);
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Ошибка разбора YAML" };
  }
}

export function skillFromYaml(raw: string, base: Skill): Skill | { error: string } {
  const parsed = parseSkillYamlDocument(raw);
  if ("error" in parsed) return parsed;

  return normalizeSkill({
    ...base,
    id: base.id,
    name: base.name,
    description: parsed.description ?? base.description,
    version: parsed.version ?? base.version,
    initial: parsed.initial ?? null,
    params: parsed.params ?? [],
    states: mergeLayout(base.states, parsed.states ?? []),
    viewport: base.viewport,
    createdAt: base.createdAt,
    updatedAt: new Date().toISOString(),
  });
}

export function mergeLayout(existing: FsmState[], imported: FsmState[]): FsmState[] {
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

function parseInlineList(value: string): string[] {
  const trimmed = value.trim();
  if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) {
    const single = String(parseScalar(trimmed));
    return single ? [single] : [];
  }
  const inner = trimmed.slice(1, -1).trim();
  if (!inner) return [];
  return inner.split(",").map((part) => String(parseScalar(part.trim())));
}

function ensureTransition(state: FsmState, event: string) {
  let transition = state.transitions.find((item) => item.event === event && !item.to);
  if (!transition) {
    transition = {
      id: createId(),
      event,
      guard: "",
      actions: [],
      to: "",
    };
    state.transitions.push(transition);
  }
  return transition;
}

function parseSimpleSkillYaml(text: string): YamlDoc {
  const lines = text.split(/\r?\n/);
  const doc: YamlDoc = { states: [], params: [], warnings: [] };
  let mode:
    | "root"
    | "states"
    | "state"
    | "on_enter"
    | "on"
    | "event"
    | "event_item"
    | "params"
    | "param_item"
    | "guards"
    | "description_block" = "root";
  let currentState: FsmState | null = null;
  let currentEvent = "";
  let currentParam: SkillParam | null = null;
  let inActions = false;
  let descriptionLines: string[] = [];

  for (const rawLine of lines) {
    if (!rawLine.trim() || rawLine.trim().startsWith("#")) continue;
    const indent = rawLine.match(/^ */)?.[0].length ?? 0;
    const line = rawLine.trim();

    if (mode === "description_block") {
      if (indent === 0) {
        doc.description = descriptionLines.join(" ").trim();
        descriptionLines = [];
        mode = "root";
      } else {
        descriptionLines.push(line);
        continue;
      }
    }

    if (indent === 0) {
      mode = "root";
      currentState = null;
      currentParam = null;
      inActions = false;
      if (line.startsWith("id:")) {
        doc.skillId = String(parseScalar(line.slice("id:".length)));
      } else if (line.startsWith("description:")) {
        const inline = line.slice("description:".length).trim();
        if (inline === ">") {
          mode = "description_block";
        } else {
          doc.description = String(parseScalar(inline));
        }
      } else if (line.startsWith("version:")) {
        doc.version = String(parseScalar(line.slice("version:".length)));
      } else if (line.startsWith("initial:")) {
        const value = parseScalar(line.slice("initial:".length));
        doc.initial = value === null ? null : String(value);
      } else if (line.startsWith("states:")) {
        mode = "states";
      } else if (line.startsWith("params:")) {
        mode = "params";
      } else if (line.startsWith("guards:")) {
        mode = "guards";
        doc.warnings!.push("Секция guards: не импортируется (нет в SKILLS_SPEC v0.1)");
      }
      continue;
    }

    if (mode === "guards") {
      continue;
    }

    if (indent === 2 && line.endsWith(":") && line !== "{}:" && mode !== "params" && mode !== "param_item") {
      const id = line.slice(0, -1).trim();
      if (id !== "on_enter" && id !== "on" && id !== "final") {
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
    }

    if (mode === "states" && indent === 2 && line.endsWith(":") && line !== "{}:") {
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
      if (indent === 4 && line.startsWith("name:")) {
        currentState.name = String(parseScalar(line.slice("name:".length)));
        mode = "state";
        continue;
      }
      if (indent === 4 && line.startsWith("on_enter:")) {
        const inline = line.slice("on_enter:".length).trim();
        if (inline && inline !== "[]") {
          if (inline.startsWith("[")) {
            currentState.onEnter.push(...parseInlineList(inline));
          } else {
            currentState.onEnter.push(String(parseScalar(inline)));
          }
        }
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
        inActions = false;
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
      if ((mode === "event" || mode === "event_item") && indent === 8) {
        let transition = currentState.transitions.at(-1);
        if (!transition || transition.event !== currentEvent || (mode === "event" && transition.to)) {
          transition = ensureTransition(currentState, currentEvent);
        }
        if (line.startsWith("guard:")) {
          transition.guard = String(parseScalar(line.slice("guard:".length)));
          inActions = false;
          mode = "event_item";
        } else if (line.startsWith("actions:")) {
          const inline = line.slice("actions:".length).trim();
          if (inline.startsWith("[")) {
            transition.actions.push(...parseInlineList(inline));
            inActions = false;
          } else {
            inActions = true;
          }
          mode = "event_item";
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
      currentParam = { name: "", type: "string", required: false };
      doc.params!.push(currentParam);
      mode = "param_item";
      continue;
    }

    if (mode === "param_item" && currentParam && indent >= 4) {
      if (line.startsWith("name:")) {
        currentParam.name = String(parseScalar(line.slice("name:".length)));
      } else if (line.startsWith("type:")) {
        currentParam.type = String(parseScalar(line.slice("type:".length)));
      } else if (line.startsWith("required:")) {
        currentParam.required = parseScalar(line.slice("required:".length)) === true;
      }
    }
  }

  if (descriptionLines.length) {
    doc.description = descriptionLines.join(" ").trim();
  }

  return doc;
}

export function collectReferencedActionIds(states: FsmState[]): string[] {
  const ids = new Set<string>();
  for (const state of states) {
    for (const actionId of state.onEnter) ids.add(actionId);
    for (const transition of state.transitions) {
      for (const actionId of transition.actions) ids.add(actionId);
    }
  }
  return [...ids];
}
