import type { Skill } from "@/features/skills/types/skill";

const DEFAULT_ENTRY_EVENT = "channel.message.received";

/** Events that can start a skill from its initial state. */
export function getSkillEntryEvents(skill: Skill): string[] {
  if (!skill.initial) {
    return [DEFAULT_ENTRY_EVENT];
  }

  const initialState = skill.states.find((state) => state.id === skill.initial);
  if (!initialState) {
    return [DEFAULT_ENTRY_EVENT];
  }

  const events = [
    ...new Set(
      initialState.transitions
        .map((transition) => transition.event.trim())
        .filter(Boolean),
    ),
  ];

  return events.length > 0 ? events : [DEFAULT_ENTRY_EVENT];
}

/** Events accepted while waiting in a non-final state (follow-up messages). */
export function getSkillFollowUpEvents(skill: Skill, currentState: string): string[] {
  const state = skill.states.find((item) => item.id === currentState);
  if (!state) {
    return [DEFAULT_ENTRY_EVENT];
  }

  const events = [
    ...new Set(
      state.transitions
        .map((transition) => transition.event.trim())
        .filter(Boolean),
    ),
  ];

  return events.length > 0 ? events : [DEFAULT_ENTRY_EVENT];
}

export function createSimConversationId(agentSlug: string): string {
  const suffix = crypto.randomUUID().slice(0, 8);
  return `sim:${agentSlug}:${suffix}`;
}
