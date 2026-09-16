import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useActions } from "@/features/actions/composables/useActions";
import type { FsmEditorState, FsmSelection } from "@/features/skills/types/fsm";
import type { Skill } from "@/features/skills/types/skill";
import {
  buildSkillIssueMaps,
  countBySeverity,
  filterIssuesForSelection,
  type SkillIssueMaps,
} from "@/features/skills/utils/skillIssueIndex";
import { validateSkill } from "@/features/skills/utils/validateSkill";

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
    return {
      ...base,
      initial: editor?.initial ?? base.initial,
      params: editor?.params ?? base.params,
      states: editor?.states ?? base.states,
      viewport: editor?.viewport ?? base.viewport,
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
