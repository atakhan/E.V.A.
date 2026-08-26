import type { CanvasDocument } from "./canvas";

export const FSM_MODULE_ID = "core.fsm";

export interface FsmModuleData {
  canvases: CanvasDocument[];
}

export function createEmptyFsmModule(): FsmModuleData {
  return { canvases: [] };
}

export function isFsmModuleData(data: unknown): data is FsmModuleData {
  return (
    typeof data === "object" &&
    data !== null &&
    "canvases" in data &&
    Array.isArray((data as FsmModuleData).canvases)
  );
}

export function getFsmModuleData(modules: Record<string, unknown>): FsmModuleData {
  const module = modules[FSM_MODULE_ID];
  if (isFsmModuleData(module)) {
    return module;
  }
  return createEmptyFsmModule();
}
