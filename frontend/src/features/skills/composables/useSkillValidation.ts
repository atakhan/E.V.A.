import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useActions } from "@/features/actions/composables/useActions";
import type { FsmEditorState } from "@/features/skills/types/fsm";
import type { Skill } from "@/features/skills/types/skill";
import {
  buildSkillIssueMaps,
  countBySeverity,
  filterIssuesForSelection,
  type SkillIssueMaps,
} from "@/features/skills/utils/skillIssueIndex";
import { validateSkill } from "@/features/skills/utils/validateSkill";
import type { FsmSelection } from "@/features/skills/types/fsm";

export function useSkillValidation(
  agentSlug: MaybeRefOrGetter<string>,
  skillSource: MaybeRefOrGetter<Skill | null | undefined>,
  editorState?: MaybeRefOrGetter<FsmEditorState | null | undefined>,
) {
  const { getActions } = useActions();

  const actionIds = computed(() => {
    const slug = toValue(agentSlug);
    return new Set(getActions(slug).map((action) => action.id));
  });

  const skillForValidation = computed<Skill | null>(() => {
    const base = toValue(skillSource);
    const editor = editorState ? toValue(editorState) : null;
    if (!base) return null;
    if (!editor) return base;
    return {
      ...base,
      initial: editor.initial,
      params: editor.params,
      states: editor.states,
      viewport: editor.viewport,
    };
  });

  const issues = computed(() => {
    const skill = skillForValidation.value;
    if (!skill) return [];
    return validateSkill(skill, actionIds.value);
  });

  const severityCounts = computed(() => countBySeverity(issues.value));

  const issueMaps = computed<SkillIssueMaps>(() => buildSkillIssueMaps(issues.value));

  function issuesForSelection(selection: FsmSelection): ReturnType<typeof filterIssuesForSelection> {
    return filterIssuesForSelection(issues.value, selection);
  }

  return {
    issues,
    errors: computed(() => severityCounts.value.errors),
    warnings: computed(() => severityCounts.value.warnings),
    infos: computed(() => severityCounts.value.infos),
    issueMaps,
    issuesForSelection,
  };
}
