import { describe, expect, it } from "vitest";
import { describeAgentHub } from "@/features/constructor/utils/agentHubStatus";
import type { AgentRuntimeSummary } from "@/features/runtime/types/runtime";

function summary(patch: Partial<AgentRuntimeSummary> = {}): AgentRuntimeSummary {
  return {
    agentSlug: "sous-letter",
    running: 0,
    waiting: 0,
    error: 0,
    completed: 0,
    cancelled: 0,
    latestPublicationVersion: "0.1.1",
    latestPublishedAt: "2026-10-12T11:37:04+00:00",
    isPublished: true,
    draftChanges: [],
    ...patch,
  };
}

describe("describeAgentHub", () => {
  it("says the agent is not published before the first publication", () => {
    const status = describeAgentHub(
      summary({ isPublished: false, latestPublicationVersion: null, latestPublishedAt: null, draftChanges: null }),
    );

    expect(status.tone).toBe("neutral");
    expect(status.headline).toBe("Не опубликован");
    expect(status.compactLine).toBe("не опубликован");
    expect(status.unpublishedParts).toEqual([]);
  });

  it("is green when the draft matches the publication", () => {
    const status = describeAgentHub(summary());

    expect(status.tone).toBe("success");
    expect(status.headline).toBe("Опубликован 0.1.1");
    expect(status.compactLine).toBe("0.1.1");
  });

  it("names the draft parts that are not published yet", () => {
    const status = describeAgentHub(summary({ draftChanges: ["skills", "tools"] }));

    expect(status.tone).toBe("warning");
    expect(status.headline).toBe("Черновик новее 0.1.1");
    expect(status.unpublishedParts).toEqual(["навыки", "плагины и каналы"]);
    expect(status.compactLine).toBe("0.1.1 · черновик новее");
  });

  it("shows active runs in the compact line and every status in the run list", () => {
    const status = describeAgentHub(summary({ running: 2, waiting: 1, error: 3, completed: 7 }));

    expect(status.activeRuns).toBe(3);
    expect(status.compactLine).toBe("0.1.1 · идут 2 · ждут 1");
    expect(status.runs.map((run) => [run.status, run.count])).toEqual([
      ["running", 2],
      ["waiting", 1],
      ["error", 3],
      ["completed", 7],
      ["cancelled", 0],
    ]);
  });
});
