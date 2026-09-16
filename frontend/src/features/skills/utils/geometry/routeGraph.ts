import type { FsmState, FsmTransition, Point } from "@/features/skills/types/fsm";
import {
  defaultAnchorsForPair,
  normalizeMagneticAnchor,
  type RectLike,
  type RoutedEdge,
  type SideAnchor,
} from "@/features/skills/utils/edgeRouting";
import type { FlowDirection } from "@/features/skills/utils/geometry/config";
import { routeOrthogonal } from "@/features/skills/utils/geometry/orthogonalRouter";
import { rectCenter } from "@/features/skills/utils/geometry/rects";
import { transitionRouteKey } from "@/features/skills/utils/geometry/validate";

export type GraphRoute = RoutedEdge & {
  cost: number;
  valid: boolean;
  fallback: boolean;
};

export interface RouteGraphOptions {
  flowDirection?: FlowDirection;
  preview?: boolean;
}

function isReturn(source: RectLike, target: RectLike, flow: FlowDirection): boolean {
  const from = rectCenter(source);
  const to = rectCenter(target);
  if (flow === "vertical") return to.y < from.y - source.height / 4;
  return to.x < from.x - source.width / 4;
}

export function resolvedAnchorsForTransition(
  source: RectLike & { id: string },
  target: RectLike & { id: string },
  transition: Pick<FsmTransition, "fromSide" | "toSide" | "fromAnchor" | "toAnchor">,
  parallelIndex: number,
): { from: SideAnchor; to: SideAnchor } {
  const defaults = defaultAnchorsForPair(source, target, parallelIndex, source.id === target.id);
  return {
    from:
      transition.fromSide !== undefined
        ? { side: transition.fromSide, anchor: normalizeMagneticAnchor(transition.fromAnchor ?? 0.5) }
        : defaults.from,
    to:
      transition.toSide !== undefined
        ? { side: transition.toSide, anchor: normalizeMagneticAnchor(transition.toAnchor ?? 0.5) }
        : defaults.to,
  };
}

function forEachTransitionPair(
  states: FsmState[],
  visit: (source: FsmState, target: FsmState, transition: FsmTransition, parallelIndex: number) => void,
) {
  const byId = new Map(states.map((state) => [state.id, state]));
  const parallelCounts = new Map<string, number>();
  for (const source of states) {
    for (const transition of source.transitions) {
      const target = byId.get(transition.to);
      if (!target) continue;
      const pairKey = `${source.id}->${target.id}`;
      const parallelIndex = parallelCounts.get(pairKey) ?? 0;
      parallelCounts.set(pairKey, parallelIndex + 1);
      visit(source, target, transition, parallelIndex);
    }
  }
}

function writePorts(transition: FsmTransition, from: SideAnchor, to: SideAnchor) {
  transition.fromSide = from.side;
  transition.fromAnchor = from.anchor;
  transition.toSide = to.side;
  transition.toAnchor = to.anchor;
}

/** Persist current ports so later moves only rebuild the polyline. */
export function pinMissingTransitionPorts(states: FsmState[]) {
  forEachTransitionPair(states, (source, target, transition, parallelIndex) => {
    if (transition.fromSide !== undefined && transition.toSide !== undefined) return;
    const resolved = resolvedAnchorsForTransition(source, target, transition, parallelIndex);
    writePorts(transition, resolved.from, resolved.to);
  });
}

/** Re-pick ports from current geometry (auto-layout). */
export function reassignTransitionPorts(states: FsmState[]) {
  forEachTransitionPair(states, (source, target, transition, parallelIndex) => {
    const defaults = defaultAnchorsForPair(source, target, parallelIndex, source.id === target.id);
    writePorts(transition, defaults.from, defaults.to);
  });
}

export function routeSkillGraph(states: FsmState[], options: RouteGraphOptions = {}): Map<string, GraphRoute> {
  const flow = options.flowDirection ?? "vertical";
  const preview = options.preview ?? false;
  const jobs: Array<{
    source: FsmState;
    target: FsmState;
    parallelIndex: number;
    isSelfLoop: boolean;
    returning: boolean;
    key: string;
    from: SideAnchor;
    to: SideAnchor;
    waypoints?: Point[];
  }> = [];

  forEachTransitionPair(states, (source, target, transition, parallelIndex) => {
    const anchors = resolvedAnchorsForTransition(source, target, transition, parallelIndex);
    jobs.push({
      source,
      target,
      parallelIndex,
      isSelfLoop: source.id === target.id,
      returning: isReturn(source, target, flow),
      key: transitionRouteKey(source.id, transition.id),
      from: anchors.from,
      to: anchors.to,
      waypoints: transition.waypoints,
    });
  });

  jobs.sort((left, right) => {
    if (left.isSelfLoop !== right.isSelfLoop) return left.isSelfLoop ? 1 : -1;
    if (left.returning !== right.returning) return left.returning ? 1 : -1;
    return left.source.y - right.source.y || left.source.x - right.source.x;
  });

  const routes = new Map<string, GraphRoute>();
  const placed: Point[][] = [];

  for (const job of jobs) {
    const routed = routeOrthogonal({
      source: job.source,
      target: job.target,
      fromAnchor: job.from,
      toAnchor: job.to,
      obstacles: states,
      waypoints: job.waypoints,
      existingRoutes: preview ? [] : placed,
      flowDirection: flow,
      parallelIndex: job.parallelIndex,
      preview,
    });
    routes.set(job.key, {
      points: routed.points,
      labelAt: routed.labelAt,
      cost: routed.cost,
      valid: routed.valid,
      fallback: routed.fallback,
    });
    placed.push(routed.points);
  }

  return routes;
}
