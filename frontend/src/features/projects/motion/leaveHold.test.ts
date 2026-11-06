import { describe, expect, it } from "vitest";
import { holdForLeave, holdFromRoute } from "@/features/projects/motion/leaveHold";

describe("leaveHold", () => {
  it("marks route-sourced holds", () => {
    expect(holdFromRoute({ projectSlug: "alpha", agentSlug: "bot" })).toEqual({
      source: "route",
      projectSlug: "alpha",
      agentSlug: "bot",
    });
  });

  it("freezes an open hold for leave after the router clears", () => {
    const open = holdFromRoute({ projectSlug: "alpha", agentSlug: "bot" });
    expect(holdForLeave(open, { projectSlug: "fallback" })).toEqual({
      source: "leave",
      projectSlug: "alpha",
      agentSlug: "bot",
    });
  });

  it("uses fallback when nothing was mounted", () => {
    expect(holdForLeave(null, { projectSlug: "alpha" })).toEqual({
      source: "leave",
      projectSlug: "alpha",
    });
  });
});
