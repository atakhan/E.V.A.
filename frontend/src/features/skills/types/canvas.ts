/** @deprecated Legacy canvas document shape — kept for storage migration. */
export interface CanvasDocument {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  rectangles: Array<{
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
  viewport: { panX: number; panY: number; zoom: number };
}
