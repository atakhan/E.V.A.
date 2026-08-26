export interface Application {
  id: string;
  slug: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  modules: Record<string, unknown>;
}

export type ApplicationInput = {
  name: string;
  slug: string;
  description?: string;
};

export type ApplicationMutationResult =
  | { ok: true; app: Application }
  | { ok: false; error: string };
