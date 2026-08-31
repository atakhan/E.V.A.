import { describe, expect, it } from "vitest";
import {
  getRecipeInputFields,
  objectToPresetValues,
  presetInputToObject,
} from "@/features/actions/utils/recipeInputPresets";

describe("recipeInputPresets", () => {
  it("round-trips web_client.send_message fields", () => {
    const fields = getRecipeInputFields("web_client", "send_message");
    expect(fields).not.toBeNull();
    const values = {
      text: "{{vars.last_message}}",
      conversation_id: "{{vars.conversation_id}}",
    };
    const object = presetInputToObject(fields!, values);
    expect(object).toEqual(values);
    expect(objectToPresetValues(fields!, object)).toEqual(values);
  });

  it("parses json field in preset", () => {
    const fields = getRecipeInputFields("llm", "run_structured");
    expect(fields).not.toBeNull();
    const object = presetInputToObject(fields!, {
      prompt: "hello",
      schema: '{"type":"object"}',
    });
    expect(object.schema).toEqual({ type: "object" });
  });
});
