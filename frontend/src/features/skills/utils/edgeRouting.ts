import { GRID_SIZE, type Point } from "@/features/skills/types/fsm";

export type RectSide = "top" | "right" | "bottom" | "left";

export interface RectLike {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SideAnchor {
  side: RectSide;
  /** Position along the edge, 0 = start, 1 = end. */
  anchor: number;
}

export interface RoutedEdge {
  points: Point[];
  labelAt: Point;
}

const ROUTE_STUB = GRID_SIZE * 1.5;
const PARALLEL_SPREAD = GRID_SIZE * 0.75;
const MAGNETIC_SNAP_DISTANCE = GRID_SIZE * 2;

export const MAGNETIC_ANCHORS = [0.25, 0.5, 0.75] as const;
export const RECT_SIDES: RectSide[] = ["top", "right", "bottom", "left"];

export interface MagneticPoint {
  side: RectSide;
  anchor: number;
  point: Point;
}

const SIDE_NORMAL: Record<RectSide, Point> = {
  top: { x: 0, y: -1 },
  right: { x: 1, y: 0 },
  bottom: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
};

export function sideFromPoint(rect: RectLike, point: Point): SideAnchor {
  const left = point.x - rect.x;
  const right = rect.x + rect.width - point.x;
  const top = point.y - rect.y;
  const bottom = rect.y + rect.height - point.y;
  const min = Math.min(left, right, top, bottom);

  if (min === top) {
    return { side: "top", anchor: clamp01(left / rect.width) };
  }
  if (min === bottom) {
    return { side: "bottom", anchor: clamp01(left / rect.width) };
  }
  if (min === left) {
    return { side: "left", anchor: clamp01(top / rect.height) };
  }
  return { side: "right", anchor: clamp01(top / rect.height) };
}

export function normalizeMagneticAnchor(anchor: number): number {
  let best: number = MAGNETIC_ANCHORS[0];
  let minDistance = Math.abs(anchor - best);
  for (const candidate of MAGNETIC_ANCHORS) {
    const distance = Math.abs(anchor - candidate);
    if (distance < minDistance) {
      minDistance = distance;
      best = candidate;
    }
  }
  return best;
}

export function snapSideAnchorFromPoint(rect: RectLike, point: Point): SideAnchor {
  const raw = sideFromPoint(rect, point);
  return {
    side: raw.side,
    anchor: normalizeMagneticAnchor(raw.anchor),
  };
}

export function magneticPointsForRect(rect: RectLike): MagneticPoint[] {
  const points: MagneticPoint[] = [];
  for (const side of RECT_SIDES) {
    for (const anchor of MAGNETIC_ANCHORS) {
      points.push({
        side,
        anchor,
        point: pointOnSide(rect, side, anchor),
      });
    }
  }
  return points;
}

export function defaultAnchorsForPair(
  from: RectLike,
  to: RectLike,
  parallelIndex: number,
  isSelfLoop: boolean,
): { from: SideAnchor; to: SideAnchor } {
  if (isSelfLoop) {
    const loops: Array<{ from: SideAnchor; to: SideAnchor }> = [
      { from: { side: "bottom", anchor: 0.25 }, to: { side: "top", anchor: 0.75 } },
      { from: { side: "right", anchor: 0.25 }, to: { side: "left", anchor: 0.75 } },
      { from: { side: "top", anchor: 0.25 }, to: { side: "bottom", anchor: 0.75 } },
      { from: { side: "left", anchor: 0.25 }, to: { side: "right", anchor: 0.75 } },
    ];
    return loops[parallelIndex % loops.length];
  }

  const fromCenter = rectCenter(from);
  const toCenter = rectCenter(to);
  const dx = toCenter.x - fromCenter.x;
  const dy = toCenter.y - fromCenter.y;

  const primaryPairs: Array<{ from: RectSide; to: RectSide }> =
    Math.abs(dx) >= Math.abs(dy)
      ? [
          { from: "right", to: "left" },
          { from: "left", to: "right" },
        ]
      : [
          { from: "bottom", to: "top" },
          { from: "top", to: "bottom" },
        ];

  const secondaryPairs: Array<{ from: RectSide; to: RectSide }> =
    Math.abs(dx) >= Math.abs(dy)
      ? [
          { from: "bottom", to: "top" },
          { from: "top", to: "bottom" },
          { from: "right", to: "top" },
          { from: "right", to: "bottom" },
        ]
      : [
          { from: "right", to: "left" },
          { from: "left", to: "right" },
          { from: "bottom", to: "left" },
          { from: "bottom", to: "right" },
        ];

  const pairs = [...primaryPairs, ...secondaryPairs];
  const pair = pairs[parallelIndex % pairs.length];
  const anchor = MAGNETIC_ANCHORS[parallelIndex % MAGNETIC_ANCHORS.length];

  return {
    from: { side: pair.from, anchor },
    to: { side: pair.to, anchor: MAGNETIC_ANCHORS[(parallelIndex + 1) % MAGNETIC_ANCHORS.length] },
  };
}

export function closestPointOnRectBorder(
  rect: RectLike,
  point: Point,
): { anchor: SideAnchor; point: Point } {
  const anchor = snapSideAnchorFromPoint(rect, point);
  return {
    anchor,
    point: pointOnSide(rect, anchor.side, anchor.anchor),
  };
}

function isNearState(point: Point, state: RectLike): boolean {
  const inside =
    point.x >= state.x &&
    point.x <= state.x + state.width &&
    point.y >= state.y &&
    point.y <= state.y + state.height;
  if (inside) return true;

  return (
    point.x >= state.x - ROUTE_STUB * 2 &&
    point.x <= state.x + state.width + ROUTE_STUB * 2 &&
    point.y >= state.y - ROUTE_STUB * 2 &&
    point.y <= state.y + state.height + ROUTE_STUB * 2
  );
}

function nearestMagneticPoint(
  state: RectLike,
  point: Point,
): { anchor: SideAnchor; point: Point; distance: number } {
  let best: { anchor: SideAnchor; point: Point; distance: number } | null = null;
  for (const magnetic of magneticPointsForRect(state)) {
    const distance = Math.hypot(magnetic.point.x - point.x, magnetic.point.y - point.y);
    if (!best || distance < best.distance) {
      best = {
        anchor: { side: magnetic.side, anchor: magnetic.anchor },
        point: magnetic.point,
        distance,
      };
    }
  }
  if (!best) {
    const anchor = snapSideAnchorFromPoint(state, point);
    return {
      anchor,
      point: pointOnSide(state, anchor.side, anchor.anchor),
      distance: Infinity,
    };
  }
  return best;
}

/** Snap connector endpoint to magnetic points on a state border. */
export function snapEndpointToState(
  point: Point,
  states: Array<RectLike & { id?: string }>,
  preferredStateId?: string,
): { stateIndex: number; anchor: SideAnchor; point: Point } | null {
  if (states.length === 0) return null;

  const candidates: Array<{
    stateIndex: number;
    anchor: SideAnchor;
    point: Point;
    distance: number;
  }> = [];

  const searchOrder = preferredStateId
    ? [
        ...states
          .map((state, index) => ({ state, index }))
          .filter((item) => item.state.id === preferredStateId),
        ...states
          .map((state, index) => ({ state, index }))
          .filter((item) => item.state.id !== preferredStateId),
      ]
    : states.map((state, index) => ({ state, index })).reverse();

  for (const { state, index } of searchOrder) {
    if (!isNearState(point, state)) continue;
    const nearest = nearestMagneticPoint(state, point);
    if (nearest.distance <= MAGNETIC_SNAP_DISTANCE) {
      candidates.push({
        stateIndex: index,
        anchor: nearest.anchor,
        point: nearest.point,
        distance: nearest.distance,
      });
    }
  }

  if (candidates.length === 0) return null;

  candidates.sort((left, right) => left.distance - right.distance);
  const best = candidates[0];
  return {
    stateIndex: best.stateIndex,
    anchor: best.anchor,
    point: best.point,
  };
}

export function pointOnSide(rect: RectLike, side: RectSide, anchor: number): Point {
  const t = clamp01(anchor);
  switch (side) {
    case "top":
      return { x: rect.x + t * rect.width, y: rect.y };
    case "bottom":
      return { x: rect.x + t * rect.width, y: rect.y + rect.height };
    case "left":
      return { x: rect.x, y: rect.y + t * rect.height };
    case "right":
      return { x: rect.x + rect.width, y: rect.y + t * rect.height };
  }
}

export function routeEdge(
  from: RectLike,
  to: RectLike,
  fromAnchor: SideAnchor,
  toAnchor: SideAnchor,
  parallelIndex = 0,
  isSelfLoop = false,
): RoutedEdge {
  const spreadSign = parallelIndex % 2 === 0 ? 1 : -1;
  const offset = Math.ceil(parallelIndex / 2) * PARALLEL_SPREAD * spreadSign;

  const start = applySideOffset(pointOnSide(from, fromAnchor.side, fromAnchor.anchor), fromAnchor.side, offset);
  const end = applySideOffset(pointOnSide(to, toAnchor.side, toAnchor.anchor), toAnchor.side, offset);

  if (isSelfLoop) {
    return routeSelfLoop(start, end, fromAnchor.side, toAnchor.side, parallelIndex);
  }

  const points = routeBetweenAnchors(start, fromAnchor.side, end, toAnchor.side);
  return {
    points,
    labelAt: labelPointOnPath(points),
  };
}

function routeSelfLoop(start: Point, end: Point, fromSide: RectSide, toSide: RectSide, parallelIndex: number): RoutedEdge {
  const loopSize = ROUTE_STUB * 2 + parallelIndex * PARALLEL_SPREAD;
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
    const corner = movePoint(p1, perpendicular(fromNormal), loopSize * (parallelIndex % 2 === 0 ? 1 : -1));
    points.push(corner, movePoint(p4, perpendicular(toNormal), loopSize * (parallelIndex % 2 === 0 ? -1 : 1)), p4);
  }

  points.push(end);
  return { points: dedupePoints(points), labelAt: labelPointOnPath(points) };
}

function routeBetweenAnchors(start: Point, fromSide: RectSide, end: Point, toSide: RectSide): Point[] {
  const fromNormal = SIDE_NORMAL[fromSide];
  const toNormal = SIDE_NORMAL[toSide];
  const p1 = movePoint(start, fromNormal, ROUTE_STUB);
  const p4 = movePoint(end, toNormal, ROUTE_STUB);

  const points: Point[] = [start, p1];

  const fromHorizontal = fromSide === "left" || fromSide === "right";
  const toHorizontal = toSide === "left" || toSide === "right";

  if (fromHorizontal && toHorizontal) {
    const midX = (p1.x + p4.x) / 2;
    points.push({ x: midX, y: p1.y }, { x: midX, y: p4.y });
  } else if (!fromHorizontal && !toHorizontal) {
    const midY = (p1.y + p4.y) / 2;
    points.push({ x: p1.x, y: midY }, { x: p4.x, y: midY });
  } else if (fromHorizontal) {
    points.push({ x: p4.x, y: p1.y });
  } else {
    points.push({ x: p1.x, y: p4.y });
  }

  points.push(p4, end);
  return dedupePoints(points);
}

export function polylineLength(points: Point[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i += 1) {
    total += Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
  }
  return total;
}

export function distanceToPolyline(point: Point, points: Point[]): number {
  if (points.length < 2) {
    return points.length === 1 ? Math.hypot(point.x - points[0].x, point.y - points[0].y) : Infinity;
  }

  let min = Infinity;
  for (let i = 1; i < points.length; i += 1) {
    min = Math.min(min, distanceToSegment(point, points[i - 1], points[i]));
  }
  return min;
}

export function polylineToPath(points: Point[]): string {
  if (points.length === 0) return "";
  const [first, ...rest] = points;
  return `M ${first.x} ${first.y} ${rest.map((point) => `L ${point.x} ${point.y}`).join(" ")}`;
}

function distanceToSegment(point: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  if (dx === 0 && dy === 0) {
    return Math.hypot(point.x - a.x, point.y - a.y);
  }
  const t = Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy));
}

function rectCenter(rect: RectLike): Point {
  return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function movePoint(point: Point, direction: Point, distance: number): Point {
  return {
    x: point.x + direction.x * distance,
    y: point.y + direction.y * distance,
  };
}

function perpendicular(direction: Point): Point {
  return { x: -direction.y, y: direction.x };
}

function applySideOffset(point: Point, side: RectSide, offset: number): Point {
  if (side === "top" || side === "bottom") {
    return { x: point.x + offset, y: point.y };
  }
  return { x: point.x, y: point.y + offset };
}

function dedupePoints(points: Point[]): Point[] {
  return points.filter((point, index) => {
    if (index === 0) return true;
    const prev = points[index - 1];
    return point.x !== prev.x || point.y !== prev.y;
  });
}

function labelPointOnPath(points: Point[]): Point {
  if (points.length < 2) {
    return points[0] ?? { x: 0, y: 0 };
  }

  const target = polylineLength(points) / 2;
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

export const EDGE_LABEL_NODE_RADIUS = 5;
export const EDGE_LABEL_LINE_GAP = 6;

function pointAlongSegment(a: Point, b: Point, distanceFromA: number): Point {
  const length = Math.hypot(b.x - a.x, b.y - a.y);
  if (length === 0) return { ...a };
  const t = distanceFromA / length;
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
  };
}

/** Split a polyline around `labelAt`, leaving a gap for a circular label badge. */
export function splitPolylineForLabel(
  points: Point[],
  labelAt: Point,
  gapRadius: number,
): { before: Point[]; after: Point[] } {
  if (points.length < 2) {
    return { before: points, after: [] };
  }

  let bestIndex = 1;
  let bestDist = Infinity;
  for (let i = 1; i < points.length; i += 1) {
    const dist = distanceToSegment(labelAt, points[i - 1], points[i]);
    if (dist < bestDist) {
      bestDist = dist;
      bestIndex = i;
    }
  }

  const a = points[bestIndex - 1];
  const b = points[bestIndex];
  const segmentLength = Math.hypot(b.x - a.x, b.y - a.y);
  if (segmentLength <= gapRadius * 2) {
    const before = points.slice(0, bestIndex);
    const after = points.slice(bestIndex);
    return { before, after };
  }

  const toLabel = Math.hypot(labelAt.x - a.x, labelAt.y - a.y);
  const cutA = pointAlongSegment(a, b, Math.max(0, toLabel - gapRadius));
  const cutB = pointAlongSegment(a, b, Math.min(segmentLength, toLabel + gapRadius));

  const before = [...points.slice(0, bestIndex - 1), a, cutA];
  const after = [cutB, ...points.slice(bestIndex)];
  return { before, after };
}
