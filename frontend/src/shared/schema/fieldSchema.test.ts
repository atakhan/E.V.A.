import { describe, expect, it } from "vitest";
import { fieldValuesToObject, validateFields } from "@/shared/schema/fieldSchema";
import type { ToolFieldDef } from "@/features/tools/types/tool";

describe("fieldSchema", () => {
  it("validates required fields", () => {
    const schema: ToolFieldDef[] = [{ id: "text", type: "string", required: true, scope: "call" }];
    const { errors } = validateFields(schema, {}, "text.replace.");
    expect(errors.length).toBeGreaterThan(0);
  });

  it("round-trips field values", () => {
    const schema: ToolFieldDef[] = [
      { id: "text", type: "template", scope: "call" },
      { id: "regex", type: "boolean", default: false, scope: "call" },
    ];
    const object = fieldValuesToObject(schema, { text: "hello", regex: "true" });
    expect(object.text).toBe("hello");
    expect(object.regex).toBe(true);
  });
});
