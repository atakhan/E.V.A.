import type { FsmEditorState } from "@/features/skills/types/fsm";
import {
  createEmptySkill,
  createEmptyFsmEditorState,
  skillToEditorState,
} from "@/features/skills/types/skill";
import type { Skill } from "@/features/skills/types/skill";
import {
  getAgentBySlug,
  replaceAgent,
  touchAgent,
} from "@/features/agents/services/agentsStorage";
import type { SkillPackApplyOptions, SkillPackEntry } from "@/features/skills/utils/skillPackImport";
import { applySkillPack } from "@/features/skills/utils/skillPackImport";

function nextSkillName(agentSlug: string): string {
  const agent = getAgentBySlug(agentSlug);
  if (!agent) return "Skill 1";
  return `Skill ${agent.skills.length + 1}`;
}

export function useSkills() {
  function getSkills(agentSlug: string): Skill[] {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return [];
    return agent.skills;
  }

  function getSkill(agentSlug: string, skillId: string): Skill | undefined {
    return getSkills(agentSlug).find((skill) => skill.id === skillId);
  }

  function createSkill(agentSlug: string, name?: string): Skill | null {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return null;

    const skill = createEmptySkill({ name: name ?? nextSkillName(agentSlug) });
    replaceAgent(
      touchAgent({
        ...agent,
        skills: [skill, ...agent.skills],
      }),
    );
    return skill;
  }

  function updateSkill(
    agentSlug: string,
    skillId: string,
    patch: Partial<FsmEditorState> & {
      name?: string;
      description?: string;
      version?: string;
    },
  ) {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return;

    const index = agent.skills.findIndex((skill) => skill.id === skillId);
    if (index === -1) return;

    const current = agent.skills[index];
    const nextSkill: Skill = {
      ...current,
      ...patch,
      updatedAt: new Date().toISOString(),
    };

    const skills = [
      ...agent.skills.slice(0, index),
      nextSkill,
      ...agent.skills.slice(index + 1),
    ];

    replaceAgent(touchAgent({ ...agent, skills }));
  }

  function replaceSkillFsm(agentSlug: string, skillId: string, editor: FsmEditorState) {
    updateSkill(agentSlug, skillId, {
      initial: editor.initial,
      params: editor.params,
      states: editor.states,
      viewport: editor.viewport,
      flowDirection: editor.flowDirection ?? "vertical",
    });
  }

  function renameSkill(agentSlug: string, skillId: string, name: string) {
    const trimmed = name.trim();
    if (!trimmed) return;
    updateSkill(agentSlug, skillId, { name: trimmed });
  }

  function deleteSkill(agentSlug: string, skillId: string) {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return;

    replaceAgent(
      touchAgent({
        ...agent,
        skills: agent.skills.filter((skill) => skill.id !== skillId),
      }),
    );
  }

  function loadEditorState(agentSlug: string, skillId: string): FsmEditorState {
    const skill = getSkill(agentSlug, skillId);
    if (!skill) return createEmptyFsmEditorState();
    return skillToEditorState(skill);
  }

  function importSkillPack(
    agentSlug: string,
    entries: SkillPackEntry[],
    options: SkillPackApplyOptions,
  ): Skill[] {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return [];
    const skills = applySkillPack(agent, entries, options);
    replaceAgent(touchAgent({ ...agent, skills }));
    return skills;
  }

  return {
    getSkills,
    getSkill,
    createSkill,
    updateSkill,
    replaceSkillFsm,
    renameSkill,
    deleteSkill,
    loadEditorState,
    importSkillPack,
  };
}
