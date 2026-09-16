import { describe, expect, it } from "vitest";
import { growStateToFitContent, sizeNeededForStateContent } from "@/features/skills/utils/canvasGeometry";

describe("state content fitting", () => {
  it("keeps short labels within the minimum box", () => {
    const size = sizeNeededForStateContent({
      id: "idle",
      name: "Idle",
      onEnter: [],
    });
    expect(size.width).toBeGreaterThanOrEqual(80);
    expect(size.height).toBeGreaterThanOrEqual(80);
  });

  it("grows a node so a long title can sit inside it", () => {
    const fitted = growStateToFitContent({
      id: "state_1",
      name: "Когда приходит новое сообщение от пользователя",
      onEnter: [],
      x: 0,
      y: 0,
      width: 80,
      height: 80,
    });
    expect(fitted.width).toBeGreaterThan(80);
    expect(fitted.width).toBeLessThanOrEqual(360);
  });
});
