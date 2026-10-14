import { computed } from "vue";
import { getAgentBySlug } from "@/features/agents/services/agentsStorage";
import {
  addSkillSlotForCount,
  createEmptyConstructorLayout,
  DEFAULT_SKILL_NODE_HEIGHT,
  DEFAULT_SKILL_NODE_WIDTH,
  skillNodePosition,
  type ConstructorSkillNode,
} from "@/features/constructor/types/constructor";

/** Stable canvas node id derived from skill id (layout is fully derived). */
function nodeIdForSkill(skillId: string): string {
  return `ctor-skill-${skillId}`;
}

export function useConstructor(agentSlug: () => string) {
  const agent = computed(() => getAgentBySlug(agentSlug()));

  const skills = computed(() => agent.value?.skills ?? []);

  const nodes = computed<ConstructorSkillNode[]>(() => {
    const list = skills.value;
    const count = list.length;
    return list.map((skill, index) => {
      const position = skillNodePosition(index, count);
      return {
        id: nodeIdForSkill(skill.id),
        skillId: skill.id,
        x: position.x,
        y: position.y,
        width: DEFAULT_SKILL_NODE_WIDTH,
        height: DEFAULT_SKILL_NODE_HEIGHT,
      };
    });
  });

  const addSkillSlot = computed(() => addSkillSlotForCount(skills.value.length));

  const isEmpty = computed(() => nodes.value.length === 0);

  const agentName = computed(() => agent.value?.name ?? "Агент");

  const layout = computed(() => ({
    nodes: nodes.value,
  }));

  function findNodeBySkillId(skillId: string): ConstructorSkillNode | undefined {
    return nodes.value.find((node) => node.skillId === skillId);
  }

  /** All agent skills are always on the canvas; returns the node for `skillId`. */
  function placeSkill(skillId: string): ConstructorSkillNode | null {
    return findNodeBySkillId(skillId) ?? null;
  }

  return {
    layout,
    nodes,
    isEmpty,
    agentName,
    placeSkill,
    findNodeBySkillId,
    addSkillSlot,
    emptyLayout: createEmptyConstructorLayout(),
  };
}
