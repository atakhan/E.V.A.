import {
  GRID_SIZE,
  MIN_STATE_SIZE,
  type DraftRect,
  type Point,
} from "@/features/skills/types/fsm";

export function snap(value: number, grid = GRID_SIZE): number {
  return Math.round(value / grid) * grid;
}

export function snapPoint(point: Point, grid = GRID_SIZE): Point {
  return { x: snap(point.x, grid), y: snap(point.y, grid) };
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function screenToWorld(
  clientX: number,
  clientY: number,
  viewportRect: DOMRect,
  panX: number,
  panY: number,
  zoom: number,
): Point {
  return {
    x: (clientX - viewportRect.left - panX) / zoom,
    y: (clientY - viewportRect.top - panY) / zoom,
  };
}

export function normalizeRect(start: Point, end: Point): DraftRect {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);

  return { x, y, width, height };
}

export function snapRect(rect: DraftRect, grid = GRID_SIZE): DraftRect {
  const x = snap(rect.x, grid);
  const y = snap(rect.y, grid);
  const right = snap(rect.x + rect.width, grid);
  const bottom = snap(rect.y + rect.height, grid);

  return {
    x,
    y,
    width: Math.max(MIN_STATE_SIZE, right - x),
    height: Math.max(MIN_STATE_SIZE, bottom - y),
  };
}

export function isValidRect(rect: DraftRect): boolean {
  return rect.width >= MIN_STATE_SIZE && rect.height >= MIN_STATE_SIZE;
}

export function stateCenter(state: { x: number; y: number; width: number; height: number }): Point {
  return {
    x: state.x + state.width / 2,
    y: state.y + state.height / 2,
  };
}

/** Edge point on rectangle border from center toward target. */
export function borderPointToward(
  from: { x: number; y: number; width: number; height: number },
  to: Point,
): Point {
  const cx = from.x + from.width / 2;
  const cy = from.y + from.height / 2;
  const dx = to.x - cx;
  const dy = to.y - cy;
  if (dx === 0 && dy === 0) {
    return { x: cx, y: from.y };
  }

  const absDx = Math.abs(dx);
  const absDy = Math.abs(dy);
  const scaleX = from.width / 2 / (absDx || 1);
  const scaleY = from.height / 2 / (absDy || 1);
  const scale = Math.min(scaleX, scaleY);

  return {
    x: cx + dx * scale,
    y: cy + dy * scale,
  };
}
