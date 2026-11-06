import { DESK_MOVE_MS } from "@/features/projects/utils/deskMotion";

export function prefersReducedDeskMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function waitDesk(ms: number): Promise<void> {
  if (prefersReducedDeskMotion()) return Promise.resolve();
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function deskFrame(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => resolve());
  });
}

/**
 * Per-view motion token so a newer enter/leave cancels an in-flight pass.
 */
export function useDeskMotion() {
  let motion = 0;

  function beginPass(): number {
    return ++motion;
  }

  function isCurrent(token: number): boolean {
    return token === motion;
  }

  /** Bump the token so any running pass exits on its next check. */
  function cancelPasses(): void {
    motion += 1;
  }

  return {
    beginPass,
    isCurrent,
    cancelPasses,
    wait: waitDesk,
    frame: deskFrame,
    reducedMotion: prefersReducedDeskMotion,
    moveMs: DESK_MOVE_MS,
  };
}

/** Gate that resolves on ConstructorView `@ready` or after a safety timeout. */
export function createConstructorReadyGate(timeoutMs = 800) {
  let readyWait: (() => void) | null = null;

  function releaseReady(): void {
    const resolve = readyWait;
    readyWait = null;
    resolve?.();
  }

  function waitForConstructor(): Promise<void> {
    return new Promise((resolve) => {
      const timer = window.setTimeout(resolve, timeoutMs);
      readyWait = () => {
        window.clearTimeout(timer);
        resolve();
      };
    });
  }

  return { releaseReady, waitForConstructor };
}
