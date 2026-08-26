import type {
  ActionDef,
  ActionInput,
  ActionMutationResult,
  ActionRecipeStep,
} from "@/features/actions/types/action";
import {
  createEmptyAction,
  createRecipeStep,
  isValidActionId,
  normalizeActionId,
} from "@/features/actions/types/normalize";
import {
  getAgentBySlug,
  replaceAgent,
  touchAgent,
} from "@/features/agents/services/agentsStorage";

export function useActions() {
  function getActions(agentSlug: string): ActionDef[] {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return [];
    return agent.actions;
  }

  function getAction(agentSlug: string, actionId: string): ActionDef | undefined {
    return getActions(agentSlug).find((action) => action.id === actionId);
  }

  function isActionIdAvailable(agentSlug: string, id: string, excludeId?: string): boolean {
    const normalized = normalizeActionId(id);
    return !getActions(agentSlug).some(
      (action) => action.id === normalized && action.id !== excludeId,
    );
  }

  function createAction(agentSlug: string, input: ActionInput): ActionMutationResult {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return { ok: false, error: "Агент не найден" };

    const name = input.name.trim();
    if (!name) return { ok: false, error: "Укажите название Action" };

    const id = normalizeActionId(input.id || name);
    if (!isValidActionId(id)) {
      return { ok: false, error: "ID: латиница, цифры и _; начинается с буквы" };
    }
    if (!isActionIdAvailable(agentSlug, id)) {
      return { ok: false, error: "Такой Action id уже есть" };
    }

    const action = createEmptyAction({
      id,
      name,
      description: input.description,
      recipe: input.recipe,
    });

    replaceAgent(
      touchAgent({
        ...agent,
        actions: [action, ...agent.actions],
      }),
    );

    return { ok: true, action };
  }

  function updateAction(
    agentSlug: string,
    actionId: string,
    patch: Partial<ActionInput> & { recipe?: ActionRecipeStep[] },
  ): ActionMutationResult {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return { ok: false, error: "Агент не найден" };

    const index = agent.actions.findIndex((action) => action.id === actionId);
    if (index === -1) return { ok: false, error: "Action не найден" };

    const current = agent.actions[index];
    const nextId =
      patch.id !== undefined ? normalizeActionId(patch.id) : current.id;

    if (!isValidActionId(nextId)) {
      return { ok: false, error: "ID: латиница, цифры и _; начинается с буквы" };
    }
    if (!isActionIdAvailable(agentSlug, nextId, actionId)) {
      return { ok: false, error: "Такой Action id уже есть" };
    }

    const next: ActionDef = {
      ...current,
      id: nextId,
      name: patch.name?.trim() || current.name,
      description: patch.description !== undefined ? patch.description.trim() : current.description,
      recipe: patch.recipe
        ? patch.recipe.map((step) => createRecipeStep(step))
        : current.recipe,
      updatedAt: new Date().toISOString(),
    };

    const actions = [
      ...agent.actions.slice(0, index),
      next,
      ...agent.actions.slice(index + 1),
    ];

    // Keep FSM references in sync when action id changes.
    const skills =
      nextId === actionId
        ? agent.skills
        : agent.skills.map((skill) => ({
            ...skill,
            states: skill.states.map((state) => ({
              ...state,
              onEnter: state.onEnter.map((item) => (item === actionId ? nextId : item)),
              transitions: state.transitions.map((transition) => ({
                ...transition,
                actions: transition.actions.map((item) => (item === actionId ? nextId : item)),
              })),
            })),
          }));

    replaceAgent(touchAgent({ ...agent, actions, skills }));
    return { ok: true, action: next };
  }

  function deleteAction(agentSlug: string, actionId: string) {
    const agent = getAgentBySlug(agentSlug);
    if (!agent) return;

    replaceAgent(
      touchAgent({
        ...agent,
        actions: agent.actions.filter((action) => action.id !== actionId),
      }),
    );
  }

  function addRecipeStep(agentSlug: string, actionId: string, step?: Partial<ActionRecipeStep>) {
    const action = getAction(agentSlug, actionId);
    if (!action) return;
    updateAction(agentSlug, actionId, {
      recipe: [...action.recipe, createRecipeStep(step)],
    });
  }

  function updateRecipeStep(
    agentSlug: string,
    actionId: string,
    stepId: string,
    patch: Partial<ActionRecipeStep>,
  ) {
    const action = getAction(agentSlug, actionId);
    if (!action) return;
    updateAction(agentSlug, actionId, {
      recipe: action.recipe.map((step) =>
        step.id === stepId ? createRecipeStep({ ...step, ...patch, id: step.id }) : step,
      ),
    });
  }

  function removeRecipeStep(agentSlug: string, actionId: string, stepId: string) {
    const action = getAction(agentSlug, actionId);
    if (!action) return;
    updateAction(agentSlug, actionId, {
      recipe: action.recipe.filter((step) => step.id !== stepId),
    });
  }

  function moveRecipeStep(agentSlug: string, actionId: string, stepId: string, direction: -1 | 1) {
    const action = getAction(agentSlug, actionId);
    if (!action) return;
    const index = action.recipe.findIndex((step) => step.id === stepId);
    const nextIndex = index + direction;
    if (index < 0 || nextIndex < 0 || nextIndex >= action.recipe.length) return;

    const recipe = [...action.recipe];
    const [item] = recipe.splice(index, 1);
    recipe.splice(nextIndex, 0, item);
    updateAction(agentSlug, actionId, { recipe });
  }

  return {
    getActions,
    getAction,
    isActionIdAvailable,
    createAction,
    updateAction,
    deleteAction,
    addRecipeStep,
    updateRecipeStep,
    removeRecipeStep,
    moveRecipeStep,
  };
}
