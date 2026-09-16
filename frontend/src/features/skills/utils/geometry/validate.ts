import type { FsmState, FsmTransition } from "@/features/skills/types/fsm";
import { MIN_STATE_SIZE } from "@/features/skills/types/fsm";
import type { RoutedEdge } from "@/features/skills/utils/edgeRouting";
import { MIN_NODE_GAP } from "@/features/skills/utils/geometry/config";
import { polylineSelfIntersects, polylineCrossesRect, rectsOverlap, rectsOverlapWithGap } from "@/features/skills/utils/geometry/rects";

export interface GeometryIssue {
  level: "error" | "warning";
  code: string;
  message: string;
  nodeId?: string;
  connectionKey?: string;
}

export function transitionRouteKey(stateId: string, transitionId: string): string {
  return `${stateId}:${transitionId}`;
}

export function validateGraphGeometry(
  states: FsmState[],
  routes: Map<string, Pick<RoutedEdge, "points"> & { valid?: boolean }>,
): GeometryIssue[] {
  const issues: GeometryIssue[] = [];
  const byId = new Map(states.map((state) => [state.id, state]));

  for (const state of states) {
    if (state.width < MIN_STATE_SIZE || state.height < MIN_STATE_SIZE) {
      issues.push({
        level: "error",
        code: "invalid_node_size",
        message: `Узел «${state.id}» меньше минимального размера`,
        nodeId: state.id,
      });
    }
    if (!Number.isFinite(state.x) || !Number.isFinite(state.y)) {
      issues.push({
        level: "error",
        code: "invalid_node_position",
        message: `Узел «${state.id}» имеет недопустимые координаты`,
        nodeId: state.id,
      });
    }
  }

  for (let i = 0; i < states.length; i += 1) {
    for (let j = i + 1; j < states.length; j += 1) {
      if (rectsOverlap(states[i], states[j]) || rectsOverlapWithGap(states[i], states[j], MIN_NODE_GAP / 2)) {
        if (rectsOverlap(states[i], states[j])) {
          issues.push({
            level: "error",
            code: "nodes_overlap",
            message: `Узлы «${states[i].id}» и «${states[j].id}» пересекаются`,
            nodeId: states[i].id,
          });
        }
      }
    }
  }

  for (const state of states) {
    for (const transition of state.transitions) {
      const key = transitionRouteKey(state.id, transition.id);
      const target = byId.get(transition.to);
      if (!target) {
        issues.push({
          level: "error",
          code: "missing_target",
          message: `Связь из «${state.id}» ссылается на неизвестный узел`,
          connectionKey: key,
        });
        continue;
      }

      const route = routes.get(key);
      if (!route || route.points.length < 2) {
        issues.push({
          level: "error",
          code: "missing_route",
          message: `Нет маршрута для перехода ${state.id} → ${transition.to}`,
          connectionKey: key,
        });
        continue;
      }

      if (route.valid === false) {
        issues.push({
          level: "error",
          code: "invalid_route",
          message: `Маршрут ${state.id} → ${transition.to} нарушает геометрию`,
          connectionKey: key,
        });
      }

      for (const node of states) {
        if (polylineCrossesRect(route.points, node)) {
          issues.push({
            level: "error",
            code: "route_crosses_node",
            message: `Связь ${state.id} → ${transition.to} пересекает узел «${node.id}»`,
            connectionKey: key,
          });
        }
      }

      if (polylineSelfIntersects(route.points)) {
        issues.push({
          level: "warning",
          code: "route_self_intersects",
          message: `Маршрут ${state.id} → ${transition.to} самопересекается`,
          connectionKey: key,
        });
      }
    }
  }

  return issues;
}

export function hasGeometryError(issues: GeometryIssue[]): boolean {
  return issues.some((issue) => issue.level === "error");
}

export function collectTransitions(states: FsmState[]): Array<{ source: FsmState; transition: FsmTransition }> {
  return states.flatMap((source) => source.transitions.map((transition) => ({ source, transition })));
}
