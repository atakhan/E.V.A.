import type { CanvasDocument, CanvasEditorState } from "@/features/modules/fsm/types/canvas";
import {
  FSM_MODULE_ID,
  getFsmModuleData,
} from "@/features/modules/fsm/types/fsmModule";
import {
  getApplicationBySlug,
  replaceApplication,
  touchApplication,
} from "@/features/applications/services/applicationsStorage";
import { createId } from "@/shared/utils/id";

function defaultViewport() {
  return { panX: 0, panY: 0, zoom: 1 };
}

function nextCanvasName(appSlug: string): string {
  const app = getApplicationBySlug(appSlug);
  if (!app) return "Холст 1";
  return `Холст ${getFsmModuleData(app.modules).canvases.length + 1}`;
}

function createCanvasDocument(appSlug: string, name?: string): CanvasDocument {
  const now = new Date().toISOString();
  return {
    id: createId(),
    name: name ?? nextCanvasName(appSlug),
    createdAt: now,
    updatedAt: now,
    rectangles: [],
    viewport: defaultViewport(),
  };
}

export function useFsmCanvases() {
  function getCanvases(appSlug: string): CanvasDocument[] {
    const app = getApplicationBySlug(appSlug);
    if (!app) return [];
    return getFsmModuleData(app.modules).canvases;
  }

  function getCanvas(appSlug: string, canvasId: string): CanvasDocument | undefined {
    return getCanvases(appSlug).find((canvas) => canvas.id === canvasId);
  }

  function createCanvas(appSlug: string, name?: string): CanvasDocument | null {
    const app = getApplicationBySlug(appSlug);
    if (!app) return null;

    const fsm = getFsmModuleData(app.modules);
    const canvas = createCanvasDocument(appSlug, name);
    const modules = {
      ...app.modules,
      [FSM_MODULE_ID]: { canvases: [canvas, ...fsm.canvases] },
    };

    replaceApplication(touchApplication({ ...app, modules }));
    return canvas;
  }

  function updateCanvas(
    appSlug: string,
    canvasId: string,
    patch: Partial<CanvasEditorState> & { name?: string },
  ) {
    const app = getApplicationBySlug(appSlug);
    if (!app) return;

    const fsm = getFsmModuleData(app.modules);
    const index = fsm.canvases.findIndex((canvas) => canvas.id === canvasId);
    if (index === -1) return;

    const current = fsm.canvases[index];
    const nextCanvas: CanvasDocument = {
      ...current,
      ...patch,
      updatedAt: new Date().toISOString(),
    };

    const canvases = [
      ...fsm.canvases.slice(0, index),
      nextCanvas,
      ...fsm.canvases.slice(index + 1),
    ];

    replaceApplication(
      touchApplication({
        ...app,
        modules: { ...app.modules, [FSM_MODULE_ID]: { canvases } },
      }),
    );
  }

  function renameCanvas(appSlug: string, canvasId: string, name: string) {
    const trimmed = name.trim();
    if (!trimmed) return;
    updateCanvas(appSlug, canvasId, { name: trimmed });
  }

  function deleteCanvas(appSlug: string, canvasId: string) {
    const app = getApplicationBySlug(appSlug);
    if (!app) return;

    const fsm = getFsmModuleData(app.modules);
    replaceApplication(
      touchApplication({
        ...app,
        modules: {
          ...app.modules,
          [FSM_MODULE_ID]: {
            canvases: fsm.canvases.filter((canvas) => canvas.id !== canvasId),
          },
        },
      }),
    );
  }

  return {
    getCanvases,
    getCanvas,
    createCanvas,
    updateCanvas,
    renameCanvas,
    deleteCanvas,
  };
}
