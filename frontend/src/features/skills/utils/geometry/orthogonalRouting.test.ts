import { describe, expect, it } from "vitest";
import type { FsmState } from "@/features/skills/types/fsm";
import { autoLayoutStates } from "@/features/skills/utils/geometry/autoLayout";
import { placeLabelOnRoute } from "@/features/skills/utils/geometry/labels";
import { resolveRectOverlap } from "@/features/skills/utils/geometry/placement";
import { routeOrthogonal } from "@/features/skills/utils/geometry/orthogonalRouter";
import {
  pinMissingTransitionPorts,
  reassignTransitionPorts,
  routeSkillGraph,
} from "@/features/skills/utils/geometry/routeGraph";
import { polylineCrossesRect } from "@/features/skills/utils/geometry/rects";
import { validateGraphGeometry } from "@/features/skills/utils/geometry/validate";
import { sideFromPoint } from "@/features/skills/utils/edgeRouting";

function state(
  id: string,
  x: number,
  y: number,
  width = 120,
  height = 64,
  transitions: FsmState["transitions"] = [],
): FsmState {
  return { id, onEnter: [], final: false, transitions, x, y, width, height };
}

function transition(id: string, to: string, extra: Partial<FsmState["transitions"][number]> = {}) {
  return {
    id,
    event: extra.event ?? "event",
    guard: extra.guard ?? "",
    actions: extra.actions ?? [],
    to,
    fromSide: extra.fromSide,
    toSide: extra.toSide,
    fromAnchor: extra.fromAnchor,
    toAnchor: extra.toAnchor,
    waypoints: extra.waypoints,
  };
}

describe("orthogonal FSM routing", () => {
  it("scenario 1: simple connection does not cross nodes", () => {
    const source = state("a", 40, 40);
    const target = state("b", 40, 280);
    const result = routeOrthogonal({
      source,
      target,
      fromAnchor: { side: "bottom", anchor: 0.5 },
      toAnchor: { side: "top", anchor: 0.5 },
      obstacles: [source, target],
    });
    expect(result.points.length).toBeGreaterThanOrEqual(2);
    expect(polylineCrossesRect(result.points, source)).toBe(false);
    expect(polylineCrossesRect(result.points, target)).toBe(false);
    expect(result.valid).toBe(true);
  });

  it("scenario 2: moving the target still avoids nodes", () => {
    const source = state("a", 40, 40);
    const target = state("b", 360, 40);
    const result = routeOrthogonal({
      source,
      target,
      fromAnchor: { side: "right", anchor: 0.5 },
      toAnchor: { side: "left", anchor: 0.5 },
      obstacles: [source, target],
    });
    expect(polylineCrossesRect(result.points, source)).toBe(false);
    expect(polylineCrossesRect(result.points, target)).toBe(false);
  });

  it("scenario 3: routes around an obstacle on the straight path", () => {
    const source = state("a", 80, 40);
    const target = state("b", 80, 360);
    const blocker = state("c", 80, 180);
    const result = routeOrthogonal({
      source,
      target,
      fromAnchor: { side: "bottom", anchor: 0.5 },
      toAnchor: { side: "top", anchor: 0.5 },
      obstacles: [source, target, blocker],
    });
    expect(polylineCrossesRect(result.points, blocker)).toBe(false);
    expect(polylineCrossesRect(result.points, source)).toBe(false);
    expect(polylineCrossesRect(result.points, target)).toBe(false);
    expect(result.valid).toBe(true);
  });

  it("scenario 4: branching edges stay distinguishable", () => {
    const source = state("a", 200, 40, 120, 64, [
      transition("t1", "b"),
      transition("t2", "c"),
    ]);
    const left = state("b", 40, 280);
    const right = state("c", 360, 280);
    const routes = routeSkillGraph([source, left, right]);
    const first = routes.get("a:t1")!;
    const second = routes.get("a:t2")!;
    expect(first.points).not.toEqual(second.points);
    expect(polylineCrossesRect(first.points, left)).toBe(false);
    expect(polylineCrossesRect(second.points, right)).toBe(false);
  });

  it("scenario 5: return edges prefer an outer corridor", () => {
    const top = state("check", 80, 40, 140, 64, [transition("fwd", "do")]);
    const mid = state("do", 80, 200, 140, 64, [transition("next", "end")]);
    const bottom = state("end", 80, 360, 140, 64, [transition("back", "check")]);
    const routes = routeSkillGraph([top, mid, bottom], { flowDirection: "vertical" });
    const back = routes.get("end:back")!;
    expect(back).toBeTruthy();
    expect(polylineCrossesRect(back.points, top)).toBe(false);
    expect(polylineCrossesRect(back.points, mid)).toBe(false);
    expect(polylineCrossesRect(back.points, bottom)).toBe(false);

    const compositionLeft = 80;
    const compositionRight = 220;
    const interiorHits = back.points.filter(
      (point) => point.x > compositionLeft + 8 && point.x < compositionRight - 8 && point.y > 50 && point.y < 350,
    );
    expect(interiorHits.length).toBeLessThan(back.points.length);
  });

  it("scenario 6: resized node is not crossed", () => {
    const source = state("a", 40, 40);
    const target = state("b", 40, 300, 240, 160);
    const result = routeOrthogonal({
      source,
      target,
      fromAnchor: { side: "bottom", anchor: 0.5 },
      toAnchor: { side: "top", anchor: 0.5 },
      obstacles: [source, target],
    });
    expect(polylineCrossesRect(result.points, target)).toBe(false);
    expect(result.valid).toBe(true);
  });

  it("scenario 7: labels stay off nodes", () => {
    const source = state("a", 40, 40);
    const target = state("b", 40, 300);
    const blocker = state("c", 40, 160);
    const result = routeOrthogonal({
      source,
      target,
      fromAnchor: { side: "bottom", anchor: 0.5 },
      toAnchor: { side: "top", anchor: 0.5 },
      obstacles: [source, target, blocker],
    });
    const placed = placeLabelOnRoute(result.points, { width: 90, height: 24 }, [source, target, blocker]);
    const label = {
      x: placed.at.x - 45,
      y: placed.at.y - 12,
      width: 90,
      height: 24,
    };
    expect(polylineCrossesRect([label as never], blocker)).toBe(false);
    expect(
      !(
        label.x < blocker.x + blocker.width &&
        label.x + label.width > blocker.x &&
        label.y < blocker.y + blocker.height &&
        label.y + label.height > blocker.y
      ),
    ).toBe(true);
  });

  it("scenario 8: waypoints are kept when they stay outside obstacles", () => {
    const source = state("a", 40, 40);
    const target = state("b", 40, 320);
    const blocker = state("c", 40, 160);
    const waypoint = { x: 320, y: 190 };
    const result = routeOrthogonal({
      source,
      target,
      fromAnchor: { side: "bottom", anchor: 0.5 },
      toAnchor: { side: "top", anchor: 0.5 },
      obstacles: [source, target, blocker],
      waypoints: [waypoint],
    });
    expect(polylineCrossesRect(result.points, blocker)).toBe(false);
    const minDistance = Math.min(
      ...result.points.map((point) => Math.hypot(point.x - waypoint.x, point.y - waypoint.y)),
    );
    expect(minDistance).toBeLessThan(80);
  });

  it("scenario 9: auto-layout separates nodes and routing is recalculated", () => {
    const states = [
      state("a", 0, 0, 120, 64, [transition("t1", "b"), transition("t2", "c")]),
      state("b", 10, 10, 120, 64, [transition("t3", "d")]),
      state("c", 20, 12, 120, 64),
      state("d", 8, 14, 120, 64),
    ];
    const laidOut = autoLayoutStates(states, "a", "vertical");
    for (let i = 0; i < laidOut.length; i += 1) {
      for (let j = i + 1; j < laidOut.length; j += 1) {
        const resolved = resolveRectOverlap(laidOut[i], [laidOut[j]], 40);
        expect(resolved.conflict).toBe(false);
        expect(laidOut[i].x === laidOut[j].x && laidOut[i].y === laidOut[j].y).toBe(false);
      }
    }
    const routes = routeSkillGraph(laidOut);
    expect(routes.size).toBe(3);
    for (const route of routes.values()) {
      for (const node of laidOut) {
        expect(polylineCrossesRect(route.points, node)).toBe(false);
      }
    }
  });

  it("scenario 10: parallel edges and cycles stay off nodes", () => {
    const states = [
      state("a", 80, 40, 140, 64, [transition("t1", "b"), transition("t2", "b", { event: "other" })]),
      state("b", 80, 240, 140, 64, [transition("back", "a")]),
      state("side", 360, 140, 120, 64),
    ];
    const routes = routeSkillGraph(states);
    expect(routes.get("a:t1")?.points).not.toEqual(routes.get("a:t2")?.points);
    for (const route of routes.values()) {
      for (const node of states) {
        expect(polylineCrossesRect(route.points, node)).toBe(false);
      }
    }
    const issues = validateGraphGeometry(states, routes);
    expect(issues.filter((issue) => issue.code === "route_crosses_node")).toHaveLength(0);
  });

  it("routes a return edge from the facing sides", () => {
    const source = state("a", 40, 280, 120, 64, [transition("t1", "b")]);
    const target = state("b", 40, 40);
    const routed = routeSkillGraph([source, target]).get("a:t1");
    expect(routed).toBeDefined();
    expect(sideFromPoint(source, routed!.points[0]).side).toBe("top");
    expect(sideFromPoint(target, routed!.points[routed!.points.length - 1]).side).toBe("bottom");
  });

  it("keeps pinned ports when a node is dragged past the diagonal", () => {
    const source = state("a", 40, 40, 120, 64, [transition("t1", "b")]);
    const target = state("b", 40, 280);
    pinMissingTransitionPorts([source, target]);
    expect(source.transitions[0].fromSide).toBe("bottom");
    expect(source.transitions[0].toSide).toBe("top");

    target.x = 400;
    target.y = 40;
    const routed = routeSkillGraph([source, target]).get("a:t1");
    expect(routed).toBeDefined();
    expect(sideFromPoint(source, routed!.points[0]).side).toBe("bottom");
    expect(sideFromPoint(target, routed!.points[routed!.points.length - 1]).side).toBe("top");
  });

  it("does not overwrite ports the user already set", () => {
    const source = state("a", 40, 40, 120, 64, [
      transition("t1", "b", { fromSide: "right", fromAnchor: 0.5, toSide: "left", toAnchor: 0.5 }),
    ]);
    const target = state("b", 40, 280);
    pinMissingTransitionPorts([source, target]);
    expect(source.transitions[0].fromSide).toBe("right");
    expect(source.transitions[0].toSide).toBe("left");
  });

  it("reassigns ports after auto-layout", () => {
    const source = state("a", 40, 40, 120, 64, [
      transition("t1", "b", { fromSide: "right", fromAnchor: 0.5, toSide: "left", toAnchor: 0.5 }),
    ]);
    const target = state("b", 400, 40);
    const laidOut = autoLayoutStates([source, target], "a", "vertical");
    reassignTransitionPorts(laidOut);
    const edge = laidOut[0].transitions[0];
    expect(edge.fromSide).toBe("bottom");
    expect(edge.toSide).toBe("top");
  });
});
