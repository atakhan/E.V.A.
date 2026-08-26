export interface ActionRecipeStep {
  id: string;
  /** Tool id from constructor catalog, e.g. llm / memory. */
  tool: string;
  /** Command within the tool, e.g. run_structured / search. */
  command: string;
  /** Free-form args (JSON/YAML fragment) until structured params exist. */
  args: string;
}

export interface ActionDef {
  id: string;
  name: string;
  description: string;
  recipe: ActionRecipeStep[];
  createdAt: string;
  updatedAt: string;
}

export type ActionInput = {
  id: string;
  name: string;
  description?: string;
  recipe?: ActionRecipeStep[];
};

export type ActionMutationResult =
  | { ok: true; action: ActionDef }
  | { ok: false; error: string };
