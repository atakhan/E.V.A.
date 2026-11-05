import type { SystemSkillRole, Skill } from "@/features/skills/types/skill";

export const TALK_TO_AGENT: SystemSkillRole = "talk_to_agent";
export const TALK_TO_HUMAN: SystemSkillRole = "talk_to_human";

export function systemSkill(role: SystemSkillRole, now = new Date().toISOString()): Skill {
  const agent = role === TALK_TO_AGENT;
  return {
    id: role,
    name: agent ? "Общение с агентом" : "Общение с человеком",
    description: agent
      ? "Системный навык. Агент принимает сообщение от другого агента. В агентов проекта он входит сразу. Сообщения человека сюда не приходят."
      : "Системный навык рантайма проекта. Человек говорит с проектом через этот навык. В агентов проекта он по умолчанию не входит.",
    version: "0.1.0",
    createdAt: now,
    updatedAt: now,
    systemRole: role,
    initial: "listening",
    params: [{ name: "conversation_id", type: "string", required: false }],
    states: [
      {
        id: "listening",
        name: "Слушает",
        onEnter: [],
        final: false,
        x: 80,
        y: 40,
        width: 160,
        height: 80,
        transitions: [
          {
            id: `${role}_heard`,
            event: agent ? "agent.message.received" : "channel.message.received",
            guard: "",
            actions: [],
            to: "listening",
          },
        ],
      },
    ],
    viewport: { panX: 0, panY: 0, zoom: 1 },
    flowDirection: "vertical",
  };
}

export function libraryAgentSkills(now = new Date().toISOString()): Skill[] {
  return [systemSkill(TALK_TO_AGENT, now)];
}
