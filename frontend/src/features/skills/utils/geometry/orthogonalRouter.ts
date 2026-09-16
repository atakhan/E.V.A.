import type { Point } from "@/features/skills/types/fsm";
import {
  pointOnSide,
  type RectLike,
  type SideAnchor,
} from "@/features/skills/utils/edgeRouting";
import {
  BEND_PENALTY,
  CROSSING_PENALTY,
  DIRECTION_PENALTY,
  INTERIOR_PENALTY,
  MAX_ROUTE_EXPANSIONS,
  NODE_ROUTING_PADDING,
  OUTER_CORRIDOR,
  PROXIMITY_PENALTY,
  ROUTE_STUB,
  type FlowDirection,
} from "@/features/skills/utils/geometry/config";
import {
  countRouteCrossings,
  inflate,
  orthogonalSegmentHitsRectInterior,
  pointInRectStrict,
  polylineCrossesRect,
  pushPointOutOfRects,
  quantize,
  rectBottom,
  rectCenter,
  rectRight,
  simplifyOrthogonal,
  unionBounds,
  uniqueSorted,
} from "@/features/skills/utils/geometry/rects";

export interface OrthogonalRouteRequest {
  source: RectLike & { id?: string };
  target: RectLike & { id?: string };
  fromAnchor: SideAnchor;
  toAnchor: SideAnchor;
  obstacles: Array<RectLike & { id?: string }>;
  waypoints?: Point[];
  existingRoutes?: Point[][];
  flowDirection?: FlowDirection;
  parallelIndex?: number;
  preview?: boolean;
}

export interface OrthogonalRouteResult {
  points: Point[];
  labelAt: Point;
  cost: number;
  valid: boolean;
  fallback: boolean;
}

const SIDE_NORMAL: Record<SideAnchor["side"], Point> = {
  top: { x: 0, y: -1 },
  right: { x: 1, y: 0 },
  bottom: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
};

const DIRS: Array<{ dx: number; dy: number; dir: number }> = [
  { dx: 1, dy: 0, dir: 0 },
  { dx: 0, dy: -1, dir: 1 },
  { dx: -1, dy: 0, dir: 2 },
  { dx: 0, dy: 1, dir: 3 },
];

function sameNode(a: RectLike & { id?: string }, b: RectLike & { id?: string }): boolean {
  if (a === b) return true;
  if (a.id && b.id) return a.id === b.id;
  return false;
}

function movePoint(point: Point, direction: Point, distance: number): Point {
  return {
    x: quantize(point.x + direction.x * distance),
    y: quantize(point.y + direction.y * distance),
  };
}

function isReturnEdge(
  source: RectLike,
  target: RectLike,
  flow: FlowDirection,
): boolean {
  if (sameNode(source, target)) return true;
  const from = rectCenter(source);
  const to = rectCenter(target);
  if (flow === "vertical") return to.y < from.y - source.height / 4;
  return to.x < from.x - source.width / 4;
}

function hardObstaclesFor(
  request: OrthogonalRouteRequest,
  padded: boolean,
): Array<RectLike & { id?: string }> {
  return request.obstacles.map((obstacle) => {
    const terminal = sameNode(obstacle, request.source) || sameNode(obstacle, request.target);
    if (terminal || !padded) return obstacle;
    return inflate(obstacle, NODE_ROUTING_PADDING);
  });
}

function segmentHitsAny(a: Point, b: Point, obstacles: RectLike[]): boolean {
  return obstacles.some((obstacle) => orthogonalSegmentHitsRectInterior(a, b, obstacle));
}

function escapePoint(
  port: Point,
  side: SideAnchor["side"],
  obstacles: RectLike[],
  extraOffset = 0,
): Point {
  const normal = SIDE_NORMAL[side];
  const max = ROUTE_STUB + extraOffset + NODE_ROUTING_PADDING * 4;
  for (let distance = ROUTE_STUB + extraOffset; distance <= max; distance += 8) {
    const candidate = movePoint(port, normal, distance);
    if (!obstacles.some((obstacle) => pointInRectStrict(candidate, obstacle))) {
      return candidate;
    }
  }
  return movePoint(port, normal, ROUTE_STUB + extraOffset);
}

function fallbackPath(start: Point, fromSide: SideAnchor["side"], end: Point, toSide: SideAnchor["side"]): Point[] {
  const fromNormal = SIDE_NORMAL[fromSide];
  const toNormal = SIDE_NORMAL[toSide];
  const p1 = movePoint(start, fromNormal, ROUTE_STUB);
  const p4 = movePoint(end, toNormal, ROUTE_STUB);
  const points: Point[] = [start, p1];
  const fromHorizontal = fromSide === "left" || fromSide === "right";
  const toHorizontal = toSide === "left" || toSide === "right";

  if (fromHorizontal && toHorizontal) {
    const midX = quantize((p1.x + p4.x) / 2);
    points.push({ x: midX, y: p1.y }, { x: midX, y: p4.y });
  } else if (!fromHorizontal && !toHorizontal) {
    const midY = quantize((p1.y + p4.y) / 2);
    points.push({ x: p1.x, y: midY }, { x: p4.x, y: midY });
  } else if (fromHorizontal) {
    points.push({ x: p4.x, y: p1.y });
  } else {
    points.push({ x: p1.x, y: p4.y });
  }

  points.push(p4, end);
  return simplifyOrthogonal(points);
}

function selfLoopPath(
  start: Point,
  end: Point,
  fromSide: SideAnchor["side"],
  toSide: SideAnchor["side"],
  parallelIndex: number,
): Point[] {
  const loopSize = ROUTE_STUB * 2 + parallelIndex * 16;
  const fromNormal = SIDE_NORMAL[fromSide];
  const toNormal = SIDE_NORMAL[toSide];
  const p1 = movePoint(start, fromNormal, ROUTE_STUB);
  const p4 = movePoint(end, toNormal, ROUTE_STUB);
  const points: Point[] = [start, p1];

  if (fromSide === "bottom" && toSide === "top") {
    const depth = Math.max(loopSize, Math.abs(p4.y - p1.y) + ROUTE_STUB);
    points.push({ x: p1.x, y: p1.y + depth }, { x: p4.x, y: p1.y + depth }, p4);
  } else if (fromSide === "top" && toSide === "bottom") {
    const depth = Math.max(loopSize, Math.abs(p4.y - p1.y) + ROUTE_STUB);
    points.push({ x: p1.x, y: p1.y - depth }, { x: p4.x, y: p1.y - depth }, p4);
  } else if (fromSide === "right" && toSide === "left") {
    const depth = Math.max(loopSize, Math.abs(p4.x - p1.x) + ROUTE_STUB);
    points.push({ x: p1.x + depth, y: p1.y }, { x: p1.x + depth, y: p4.y }, p4);
  } else if (fromSide === "left" && toSide === "right") {
    const depth = Math.max(loopSize, Math.abs(p4.x - p1.x) + ROUTE_STUB);
    points.push({ x: p1.x - depth, y: p1.y }, { x: p1.x - depth, y: p4.y }, p4);
  } else {
    const sign = parallelIndex % 2 === 0 ? 1 : -1;
    const corner = {
      x: p1.x + -fromNormal.y * loopSize * sign,
      y: p1.y + fromNormal.x * loopSize * sign,
    };
    points.push(corner, { x: p4.x, y: corner.y }, p4);
  }

  points.push(end);
  return simplifyOrthogonal(points);
}

function pathValid(points: Point[], obstacles: RectLike[]): boolean {
  if (points.length < 2) return false;
  return !obstacles.some((obstacle) => polylineCrossesRect(points, obstacle));
}

function labelPointOnPath(points: Point[]): Point {
  if (points.length < 2) return points[0] ?? { x: 0, y: 0 };
  let total = 0;
  for (let i = 1; i < points.length; i += 1) {
    total += Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
  }
  const target = total / 2;
  let walked = 0;
  for (let i = 1; i < points.length; i += 1) {
    const segment = Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
    if (walked + segment >= target) {
      const t = segment === 0 ? 0 : (target - walked) / segment;
      return {
        x: points[i - 1].x + (points[i].x - points[i - 1].x) * t,
        y: points[i - 1].y + (points[i].y - points[i - 1].y) * t,
      };
    }
    walked += segment;
  }
  return points[Math.floor(points.length / 2)];
}

function buildAxes(
  start: Point,
  end: Point,
  obstacles: RectLike[],
  waypoints: Point[],
  bounds: RectLike,
): { xs: number[]; ys: number[] } {
  const xs: number[] = [start.x, end.x, bounds.x, rectRight(bounds)];
  const ys: number[] = [start.y, end.y, bounds.y, rectBottom(bounds)];
  for (const waypoint of waypoints) {
    xs.push(waypoint.x);
    ys.push(waypoint.y);
  }
  for (const obstacle of obstacles) {
    xs.push(obstacle.x, rectRight(obstacle), obstacle.x - 8, rectRight(obstacle) + 8);
    ys.push(obstacle.y, rectBottom(obstacle), obstacle.y - 8, rectBottom(obstacle) + 8);
  }
  return { xs: uniqueSorted(xs), ys: uniqueSorted(ys) };
}

function nearestIndex(values: number[], value: number): number {
  let best = 0;
  let bestDist = Math.abs(values[0] - value);
  for (let i = 1; i < values.length; i += 1) {
    const dist = Math.abs(values[i] - value);
    if (dist < bestDist) {
      best = i;
      bestDist = dist;
    }
  }
  return best;
}

function astar(
  start: Point,
  goal: Point,
  obstacles: RectLike[],
  bounds: RectLike,
  waypoints: Point[],
  existingRoutes: Point[][],
  preview: boolean,
  flow: FlowDirection,
  returning: boolean,
): { points: Point[]; cost: number } | null {
  const { xs, ys } = buildAxes(start, goal, obstacles, waypoints, bounds);
  if (xs.length === 0 || ys.length === 0) return null;

  const walkable: boolean[][] = ys.map((_, row) =>
    xs.map((x, _col) => !obstacles.some((obstacle) => pointInRectStrict({ x, y: ys[row] }, obstacle))),
  );

  function findWalkable(point: Point): { i: number; j: number } | null {
    const i0 = nearestIndex(xs, point.x);
    const j0 = nearestIndex(ys, point.y);
    if (walkable[j0]?.[i0]) return { i: i0, j: j0 };
    const maxRadius = Math.max(xs.length, ys.length);
    for (let radius = 1; radius <= maxRadius; radius += 1) {
      for (let dj = -radius; dj <= radius; dj += 1) {
        for (let di = -radius; di <= radius; di += 1) {
          if (Math.abs(di) !== radius && Math.abs(dj) !== radius) continue;
          const i = i0 + di;
          const j = j0 + dj;
          if (j < 0 || j >= ys.length || i < 0 || i >= xs.length) continue;
          if (walkable[j][i]) return { i, j };
        }
      }
    }
    return null;
  }

  const startCell = findWalkable(start);
  const goalCell = findWalkable(goal);
  if (!startCell || !goalCell) return null;
  const goalI = goalCell.i;
  const goalJ = goalCell.j;
  const startI = startCell.i;
  const startJ = startCell.j;

  type SearchNode = { i: number; j: number; dir: number; g: number; f: number; parent: number };

  const open: SearchNode[] = [];
  const bestG = new Map<string, number>();
  const nodes: SearchNode[] = [];

  function key(i: number, j: number, dir: number): string {
    return `${i},${j},${dir}`;
  }

  function heuristic(i: number, j: number): number {
    return Math.abs(xs[i] - xs[goalI]) + Math.abs(ys[j] - ys[goalJ]);
  }

  const startNode: SearchNode = {
    i: startI,
    j: startJ,
    dir: -1,
    g: 0,
    f: heuristic(startI, startJ),
    parent: -1,
  };
  open.push(startNode);
  nodes.push(startNode);
  bestG.set(key(startI, startJ, -1), 0);

  let expansions = 0;
  let goalIndex = -1;

  while (open.length > 0 && expansions < MAX_ROUTE_EXPANSIONS) {
    expansions += 1;
    let best = 0;
    for (let index = 1; index < open.length; index += 1) {
      if (open[index].f < open[best].f) best = index;
    }
    const current = open.splice(best, 1)[0];
    const currentIndex = nodes.indexOf(current);

    if (current.i === goalI && current.j === goalJ) {
      goalIndex = currentIndex;
      break;
    }

    const from: Point = { x: xs[current.i], y: ys[current.j] };

    for (const step of DIRS) {
      const i = current.i + step.dx;
      const j = current.j + step.dy;
      if (j < 0 || j >= ys.length || i < 0 || i >= xs.length) continue;
      if (!walkable[j][i]) continue;

      const to: Point = { x: xs[i], y: ys[j] };
      if (segmentHitsAny(from, to, obstacles)) continue;

      const length = Math.abs(to.x - from.x) + Math.abs(to.y - from.y);
      if (length === 0) continue;

      const bend = current.dir !== -1 && current.dir !== step.dir ? BEND_PENALTY : 0;
      const crossings = preview ? 0 : countRouteCrossings(from, to, existingRoutes) * CROSSING_PENALTY;
      let directionTax = 0;
      if (!returning) {
        if (flow === "vertical" && step.dir === 1) directionTax = DIRECTION_PENALTY * length;
        if (flow === "horizontal" && step.dir === 2) directionTax = DIRECTION_PENALTY * length;
      }
      let interiorTax = 0;
      if (returning) {
        const mid = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 };
        const inner = inflate(bounds, -OUTER_CORRIDOR / 2);
        if (inner.width > 0 && inner.height > 0 && pointInRectStrict(mid, inner, 0)) {
          interiorTax = INTERIOR_PENALTY * length;
        }
      }
      const proximity = preview
        ? 0
        : obstacles.reduce((sum, obstacle) => {
            const padded = inflate(obstacle, NODE_ROUTING_PADDING);
            if (orthogonalSegmentHitsRectInterior(from, to, padded) && !orthogonalSegmentHitsRectInterior(from, to, obstacle)) {
              return sum + PROXIMITY_PENALTY * length;
            }
            return sum;
          }, 0);

      const g = current.g + length + bend + crossings + directionTax + interiorTax + proximity;
      const stateKey = key(i, j, step.dir);
      const previous = bestG.get(stateKey);
      if (previous !== undefined && g >= previous) continue;
      bestG.set(stateKey, g);

      const next: SearchNode = {
        i,
        j,
        dir: step.dir,
        g,
        f: g + heuristic(i, j),
        parent: currentIndex,
      };
      nodes.push(next);
      open.push(next);
    }
  }

  if (goalIndex < 0) return null;

  const cells: Point[] = [];
  let cursor: number | undefined = goalIndex;
  while (cursor !== undefined && cursor >= 0) {
    const node: SearchNode = nodes[cursor];
    cells.push({ x: xs[node.i], y: ys[node.j] });
    cursor = node.parent >= 0 ? node.parent : undefined;
  }
  cells.reverse();

  const points = simplifyOrthogonal([start, ...cells, goal]);
  return { points, cost: nodes[goalIndex].g };
}

function connectViaPoints(
  points: Point[],
  obstacles: RectLike[],
  bounds: RectLike,
  existingRoutes: Point[][],
  preview: boolean,
  flow: FlowDirection,
  returning: boolean,
): { points: Point[]; cost: number } | null {
  if (points.length < 2) return null;
  const combined: Point[] = [points[0]];
  let cost = 0;
  for (let i = 1; i < points.length; i += 1) {
    const piece = astar(
      points[i - 1],
      points[i],
      obstacles,
      bounds,
      [],
      existingRoutes,
      preview,
      flow,
      returning,
    );
    if (!piece) return null;
    cost += piece.cost;
    combined.push(...piece.points.slice(1));
  }
  return { points: simplifyOrthogonal(combined), cost };
}

export function routeOrthogonal(request: OrthogonalRouteRequest): OrthogonalRouteResult {
  const flow = request.flowDirection ?? "vertical";
  const parallelIndex = request.parallelIndex ?? 0;
  const preview = request.preview ?? false;
  const isSelfLoop = sameNode(request.source, request.target);
  const spreadSign = parallelIndex % 2 === 0 ? 1 : -1;
  const offset = Math.ceil(parallelIndex / 2) * 15 * spreadSign;

  const startPort = applySideOffset(
    pointOnSide(request.source, request.fromAnchor.side, request.fromAnchor.anchor),
    request.fromAnchor.side,
    offset,
  );
  const endPort = applySideOffset(
    pointOnSide(request.target, request.toAnchor.side, request.toAnchor.anchor),
    request.toAnchor.side,
    offset,
  );

  const paddedHard = hardObstaclesFor(request, true);
  const tightHard = hardObstaclesFor(request, false);
  const bounds = unionBounds(request.obstacles.length > 0 ? request.obstacles : [request.source, request.target], OUTER_CORRIDOR);
  const returning = isReturnEdge(request.source, request.target, flow);
  const existingRoutes = request.existingRoutes ?? [];

  const extraStub = Math.abs(offset);
  const stubStart = escapePoint(startPort, request.fromAnchor.side, paddedHard, extraStub);
  const stubEnd = escapePoint(endPort, request.toAnchor.side, paddedHard, extraStub);

  const rawWaypoints = (request.waypoints ?? []).map((point) => pushPointOutOfRects(point, paddedHard));
  const via = [stubStart, ...rawWaypoints, stubEnd];

  if (isSelfLoop && rawWaypoints.length === 0) {
    const loop = selfLoopPath(startPort, endPort, request.fromAnchor.side, request.toAnchor.side, parallelIndex);
    const others = request.obstacles.filter((obstacle) => !sameNode(obstacle, request.source));
    if (pathValid(loop, others)) {
      return {
        points: loop,
        labelAt: labelPointOnPath(loop),
        cost: 0,
        valid: true,
        fallback: false,
      };
    }
  }

  const routed =
    connectViaPoints(via, paddedHard, bounds, existingRoutes, preview, flow, returning) ??
    connectViaPoints(via, tightHard, bounds, existingRoutes, preview, flow, returning);

  if (routed) {
    const points = simplifyOrthogonal([startPort, ...routed.points, endPort]);
    const valid = pathValid(points, tightHard);
    return {
      points,
      labelAt: labelPointOnPath(points),
      cost: routed.cost,
      valid,
      fallback: false,
    };
  }

  const fallback = isSelfLoop
    ? selfLoopPath(startPort, endPort, request.fromAnchor.side, request.toAnchor.side, parallelIndex)
    : fallbackPath(startPort, request.fromAnchor.side, endPort, request.toAnchor.side);

  return {
    points: fallback,
    labelAt: labelPointOnPath(fallback),
    cost: Number.POSITIVE_INFINITY,
    valid: pathValid(fallback, tightHard),
    fallback: true,
  };
}

function applySideOffset(point: Point, side: SideAnchor["side"], offset: number): Point {
  if (side === "top" || side === "bottom") {
    return { x: quantize(point.x + offset), y: quantize(point.y) };
  }
  return { x: quantize(point.x), y: quantize(point.y + offset) };
}
