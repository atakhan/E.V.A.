export const GRID_SIZE = 20;
export const MIN_RECT_SIZE = GRID_SIZE;

export type CanvasTool = "select" | "rectangle";

export interface CanvasRect {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface Viewport {
  panX: number;
  panY: number;
  zoom: number;
}

export interface CanvasEditorState {
  rectangles: CanvasRect[];
  viewport: Viewport;
}

export interface CanvasDocument {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  rectangles: CanvasRect[];
  viewport: Viewport;
}

export interface DraftRect {
  x: number;
  y: number;
  width: number;
  height: number;
}
