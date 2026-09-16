import {
  GRID_SIZE,
  MIN_STATE_SIZE,
  type DraftRect,
  type Point,
  type ResizeHandle,
} from "@/features/skills/types/fsm";
import { formatUmlEntryLine } from "@/features/skills/utils/fsmLabelFormat";

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

export function resizeHandlePosition(
  rect: DraftRect,
  handle: ResizeHandle,
): Point {
  const { x, y, width, height } = rect;
  const cx = x + width / 2;
  const cy = y + height / 2;
  switch (handle) {
    case "nw":
      return { x, y };
    case "n":
      return { x: cx, y };
    case "ne":
      return { x: x + width, y };
    case "e":
      return { x: x + width, y: cy };
    case "se":
      return { x: x + width, y: y + height };
    case "s":
      return { x: cx, y: y + height };
    case "sw":
      return { x, y: y + height };
    case "w":
      return { x, y: cy };
  }
}

export function findResizeHandleAt(
  rect: DraftRect,
  point: Point,
  threshold: number,
): ResizeHandle | null {
  for (const handle of ["nw", "n", "ne", "e", "se", "s", "sw", "w"] as ResizeHandle[]) {
    const pos = resizeHandlePosition(rect, handle);
    if (Math.hypot(point.x - pos.x, point.y - pos.y) <= threshold) {
      return handle;
    }
  }
  return null;
}

export function resizeRectFromHandle(
  start: DraftRect,
  handle: ResizeHandle,
  pointer: Point,
  minSize = MIN_STATE_SIZE,
): DraftRect {
  let { x, y, width, height } = start;
  const right = x + width;
  const bottom = y + height;
  const px = snap(pointer.x);
  const py = snap(pointer.y);

  if (handle.includes("e")) {
    width = Math.max(minSize, px - x);
  }
  if (handle.includes("w")) {
    const nextX = Math.min(px, right - minSize);
    width = right - nextX;
    x = nextX;
  }
  if (handle.includes("s")) {
    height = Math.max(minSize, py - y);
  }
  if (handle.includes("n")) {
    const nextY = Math.min(py, bottom - minSize);
    height = bottom - nextY;
    y = nextY;
  }

  return snapRect({ x, y, width, height });
}

export function stateDisplayName(state: { id: string; name?: string }): string {
  const trimmed = state.name?.trim();
  return trimmed || state.id;
}

const STATE_PAD_X = 28;
const STATE_PAD_Y = 22;
const STATE_NAME_CHAR = 8;
const STATE_ENTRY_CHAR = 5.5;
const STATE_LINE_NAME = 18;
const STATE_LINE_ENTRY = 14;
const STATE_MAX_WIDTH = GRID_SIZE * 18;
const STATE_MAX_HEIGHT = GRID_SIZE * 10;

/** Minimum box that can hold the state's visible text without spilling. */
export function sizeNeededForStateContent(state: {
  id: string;
  name?: string;
  onEnter: string[];
  final?: boolean;
}): { width: number; height: number } {
  const title = stateDisplayName(state);
  const entry = formatUmlEntryLine(state.onEnter);
  const width = Math.max(
    MIN_STATE_SIZE,
    title.length * STATE_NAME_CHAR + STATE_PAD_X + (state.final ? 18 : 0),
    entry ? Math.min(STATE_MAX_WIDTH, entry.length * STATE_ENTRY_CHAR + STATE_PAD_X) : 0,
  );
  const extraIdLine = state.name?.trim() ? 12 : 0;
  const height = Math.max(
    MIN_STATE_SIZE,
    STATE_PAD_Y + STATE_LINE_NAME + extraIdLine + (entry ? STATE_LINE_ENTRY + 4 : 0),
  );
  return {
    width: snap(Math.min(STATE_MAX_WIDTH, width)),
    height: snap(Math.min(STATE_MAX_HEIGHT, height)),
  };
}

export function growStateToFitContent<T extends { width: number; height: number }>(
  state: T & { id: string; name?: string; onEnter: string[]; final?: boolean },
): T {
  const needed = sizeNeededForStateContent(state);
  const width = Math.max(state.width, needed.width);
  const height = Math.max(state.height, needed.height);
  if (width === state.width && height === state.height) return state;
  return { ...state, width, height };
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
