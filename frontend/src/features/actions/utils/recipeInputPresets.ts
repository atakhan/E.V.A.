export type RecipeFieldKind = "text" | "json" | "template";

export interface RecipeInputField {
  key: string;
  label: string;
  placeholder?: string;
  kind: RecipeFieldKind;
}

const PRESETS: Record<string, RecipeInputField[]> = {
  "polza_ai_llm.run": [
    { key: "messages", label: "Messages (JSON)", kind: "json", placeholder: '[{"role":"user","content":"{{vars.last_message}}"}]' },
    { key: "model", label: "Model", kind: "text", placeholder: "gpt-4o-mini" },
    { key: "temperature", label: "Temperature", kind: "text", placeholder: "0.2" },
  ],
  "polza_ai_llm.run_structured": [
    { key: "messages", label: "Messages (JSON)", kind: "json" },
    { key: "schema", label: "Schema (JSON)", kind: "json" },
    { key: "model", label: "Model", kind: "text" },
  ],
  "polza_ai_llm.parse_request": [
    { key: "text", label: "Text", kind: "template", placeholder: "{{vars.last_message}}" },
    { key: "schema", label: "Schema (JSON)", kind: "json" },
  ],
  "llm.run": [
    { key: "prompt", label: "Prompt", kind: "template", placeholder: "{{vars.last_message}}" },
  ],
  "llm.run_structured": [
    { key: "prompt", label: "Prompt", kind: "template" },
    { key: "schema", label: "Schema (JSON)", kind: "json" },
  ],
  "web_client.send_message": [
    { key: "text", label: "Text", kind: "template", placeholder: "{{vars.last_message}}" },
    { key: "conversation_id", label: "conversation_id", kind: "template", placeholder: "{{vars.conversation_id}}" },
  ],
  "telegram.send_message": [
    { key: "text", label: "Text", kind: "template", placeholder: "{{vars.last_message}}" },
    { key: "chat_id", label: "chat_id", kind: "template" },
  ],
};

export function recipePresetKey(toolId: string, command: string): string {
  return `${toolId}.${command}`;
}

export function getRecipeInputFields(toolId: string, command: string): RecipeInputField[] | null {
  return PRESETS[recipePresetKey(toolId, command)] ?? null;
}

export function presetInputToObject(
  fields: RecipeInputField[],
  values: Record<string, string>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = values[field.key] ?? "";
    if (!raw.trim()) continue;
    if (field.kind === "json") {
      try {
        result[field.key] = JSON.parse(raw);
      } catch {
        result[field.key] = raw;
      }
    } else {
      result[field.key] = raw;
    }
  }
  return result;
}

export function objectToPresetValues(
  fields: RecipeInputField[],
  input: Record<string, unknown>,
): Record<string, string> {
  const values: Record<string, string> = {};
  for (const field of fields) {
    const raw = input[field.key];
    if (raw == null) {
      values[field.key] = "";
      continue;
    }
    values[field.key] =
      field.kind === "json" && typeof raw === "object" ? JSON.stringify(raw, null, 2) : String(raw);
  }
  return values;
}

export function genericFieldsFromInput(input: Record<string, unknown>): RecipeInputField[] {
  return Object.keys(input).map((key) => ({
    key,
    label: key,
    kind: typeof input[key] === "object" ? "json" : "template",
  }));
}
