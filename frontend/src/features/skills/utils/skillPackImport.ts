import type { Agent } from "@/features/agents/types/agent";
import type { Skill } from "@/features/skills/types/skill";
import { createEmptySkill } from "@/features/skills/types/skill";
import {
  collectReferencedActionIds,
  mergeLayout,
  normalizeImportedSkillId,
  parseSkillYamlDocument,
} from "@/features/skills/utils/skillYaml";
import { normalizeSkill } from "@/features/skills/types/skill";
import { createId } from "@/shared/utils/id";

export interface SkillPackFile {
  fileName: string;
  content: string;
}

export interface SkillPackEntry {
  fileName: string;
  skillId: string;
  name: string;
  statesCount: number;
  referencedActionIds: string[];
  missingActionIds: string[];
  warnings: string[];
  skill: Skill | null;
  error?: string;
  conflict?: { existingName: string };
}

export interface SkillPackPreview {
  entries: SkillPackEntry[];
  importableCount: number;
}

export interface SkillPackApplyOptions {
  onConflict: "skip" | "replace";
}

function skillNameFromImport(skillId: string, description?: string): string {
  if (description?.trim()) {
    const firstLine = description.trim().split("\n")[0] ?? "";
    if (firstLine.length <= 80) return firstLine;
  }
  return skillId.replace(/[._-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function previewSkillPack(files: SkillPackFile[], agent: Agent): SkillPackPreview {
  const existingById = new Map(agent.skills.map((skill) => [skill.id, skill]));
  const actionIds = new Set(agent.actions.map((action) => action.id));

  const entries: SkillPackEntry[] = files.map((file) => {
    const fallbackId = normalizeImportedSkillId(
      file.fileName.replace(/\.(ya?ml)$/i, ""),
      createId(),
    );
    const parsed = parseSkillYamlDocument(file.content);
    if ("error" in parsed) {
      return {
        fileName: file.fileName,
        skillId: fallbackId,
        name: fallbackId,
        statesCount: 0,
        referencedActionIds: [],
        missingActionIds: [],
        warnings: [],
        skill: null,
        error: parsed.error,
      };
    }

    const skillId = normalizeImportedSkillId(parsed.skillId, fallbackId);
    const states = parsed.states ?? [];
    const referencedActionIds = collectReferencedActionIds(states);
    const missingActionIds = referencedActionIds.filter((id) => !actionIds.has(id));
    const existing = existingById.get(skillId);

    const skill = normalizeSkill({
      ...createEmptySkill({ name: skillNameFromImport(skillId, parsed.description), id: skillId }),
      description: parsed.description ?? "",
      version: parsed.version ?? "0.1.0",
      initial: parsed.initial ?? null,
      params: parsed.params ?? [],
      states: mergeLayout([], states),
    });

    return {
      fileName: file.fileName,
      skillId,
      name: skill.name,
      statesCount: states.length,
      referencedActionIds,
      missingActionIds,
      warnings: parsed.warnings ?? [],
      skill,
      conflict: existing ? { existingName: existing.name } : undefined,
    };
  });

  return {
    entries,
    importableCount: entries.filter((entry) => entry.skill && !entry.error).length,
  };
}

export function applySkillPack(
  agent: Agent,
  entries: SkillPackEntry[],
  options: SkillPackApplyOptions,
): Skill[] {
  const nextSkills = [...agent.skills];

  for (const entry of entries) {
    if (!entry.skill || entry.error) continue;
    const index = nextSkills.findIndex((skill) => skill.id === entry.skillId);
    if (index >= 0) {
      if (options.onConflict === "skip") continue;
      const existing = nextSkills[index]!;
      nextSkills[index] = normalizeSkill({
        ...entry.skill,
        createdAt: existing.createdAt,
        states: mergeLayout(existing.states, entry.skill.states),
        viewport: existing.viewport,
      });
    } else {
      nextSkills.unshift(entry.skill);
    }
  }

  return nextSkills;
}
