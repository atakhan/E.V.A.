import { describe, expect, it } from "vitest";
import {
  formatUmlEntryLine,
  formatUmlTransitionLabel,
} from "@/features/skills/utils/fsmLabelFormat";

describe("fsmLabelFormat", () => {
  it("formats UML transition with guard and actions", () => {
    const label = formatUmlTransitionLabel(
      "channel.message.received",
      "result.ok == true",
      ["parse_request"],
      true,
      100,
    );
    expect(label.triggerLine).toContain("channel.message.received");
    expect(label.triggerLine).toContain("[result.ok == true]");
    expect(label.actionLine).toBe("/ parse_request");
    expect(label.title).toContain("/ parse_request");
  });

  it("truncates guard when not selected", () => {
    const label = formatUmlTransitionLabel(
      "event",
      "result.missing_fields.length > 0",
      [],
      false,
      50,
    );
    expect(label.triggerLine).toContain("[");
    expect(label.triggerLine).toContain("…");
    expect(label.actionLine).toBeNull();
  });

  it("truncates long action lines so they stay in the label card", () => {
    const label = formatUmlTransitionLabel(
      "event",
      "",
      ["very_long_action_name_that_should_not_spill"],
      false,
      80,
    );
    expect(label.actionLine).toContain("…");
    expect(label.actionLine!.length).toBeLessThanOrEqual(24);
    expect(label.width).toBeLessThanOrEqual(200);
  });

  it("formats entry line for state", () => {
    expect(formatUmlEntryLine(["greet", "track"])).toBe("entry / greet, track");
    expect(formatUmlEntryLine([])).toBeNull();
  });
});
