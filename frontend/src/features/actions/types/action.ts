export type ActionPolicy = "auto" | "needs_human";

export interface ActionRecipeStep {
  id: string;
  /** Tool instance id (enabled binding). Legacy: type id when single instance. */
  tool: string;
  /** Command within the tool, e.g. run_structured / search. */
  command: string;
  /** Step input object with {{template}} expressions. */
  input: Record<string, unknown>;
  /** Optional guard expression; step runs only when true. */
  when?: string;
}

export interface ActionDef {
  id: string;
  name: string;
  description: string;
  version: string;
  policy: ActionPolicy;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  recipe: ActionRecipeStep[];
  createdAt: string;
  updatedAt: string;
}

export type ActionInput = {
  id: string;
  name: string;
  description?: string;
  version?: string;
  policy?: ActionPolicy;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  recipe?: ActionRecipeStep[];
};

export type ActionMutationResult =
  | { ok: true; action: ActionDef }
  | { ok: false; error: string };
