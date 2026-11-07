import { describe, expect, it, vi } from "vitest";
import { HANDOFF_PHASES, runHandoff } from "@/features/projects/motion/handoff";

describe("runHandoff", () => {
  it("lands before dropping, with a frame in between", async () => {
    const order: string[] = [];
    const { ok, phases } = await runHandoff(
      {
        land: () => order.push("land-action"),
        drop: () => order.push("drop-action"),
      },
      { waitFrame: async () => { order.push("wait"); } },
    );

    expect(ok).toBe(true);
    expect(phases).toEqual([...HANDOFF_PHASES]);
    expect(order).toEqual(["land-action", "wait", "drop-action"]);
  });

  it("skips drop when cancelled after the frame", async () => {
    const drop = vi.fn();
    const { ok, phases } = await runHandoff(
      { land: () => undefined, drop },
      {
        waitFrame: async () => undefined,
        cancelled: () => true,
      },
    );

    expect(ok).toBe(false);
    expect(phases).toEqual(["land", "frame"]);
    expect(drop).not.toHaveBeenCalled();
  });
});
