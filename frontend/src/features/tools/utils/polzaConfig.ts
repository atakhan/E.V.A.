/** Helpers for PolzaAI_LLM binding config stored in configNote as JSON. */

export interface PolzaBindingConfig {
  model?: string;
  note?: string;
}

export function parsePolzaConfigNote(raw: string | undefined | null): PolzaBindingConfig {
  const text = (raw ?? "").trim();
  if (!text) return {};
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      return {
        model: typeof parsed.model === "string" ? parsed.model : undefined,
        note: typeof parsed.note === "string" ? parsed.note : undefined,
      };
    } catch {
      return { note: text };
    }
  }
  return { note: text };
}

export function serializePolzaConfigNote(config: PolzaBindingConfig): string {
  const payload: Record<string, string> = {};
  if (config.model?.trim()) payload.model = config.model.trim();
  if (config.note?.trim()) payload.note = config.note.trim();
  if (!Object.keys(payload).length) return "";
  if (payload.model && !payload.note) {
    return JSON.stringify({ model: payload.model });
  }
  return JSON.stringify(payload);
}
