import { nextTick } from "vue";
import { deskFrame } from "@/features/projects/motion/useDeskMotion";

/**
 * Seat handoff order (invariant 8): land destination → wait a frame → drop flyer.
 * Opacity snaps; never fade the seat.
 */
export const HANDOFF_PHASES = ["land", "frame", "drop"] as const;
export type HandoffPhase = (typeof HANDOFF_PHASES)[number];

export type HandoffActions = {
  land: () => void;
  drop: () => void;
};

/**
 * Pure handoff sequencer — records phase order for tests; drives land/drop for runtime.
 * `waitFrame` is injected so tests stay sync-friendly.
 */
export async function runHandoff(
  actions: HandoffActions,
  options: {
    waitFrame: () => Promise<void>;
    cancelled?: () => boolean;
  },
): Promise<{ ok: boolean; phases: HandoffPhase[] }> {
  const phases: HandoffPhase[] = [];
  actions.land();
  phases.push("land");
  await options.waitFrame();
  phases.push("frame");
  if (options.cancelled?.()) {
    return { ok: false, phases };
  }
  actions.drop();
  phases.push("drop");
  return { ok: true, phases };
}

/**
 * Seat handoff: land the destination first (opacity snap), then drop the flyer
 * on the next frame — avoids end-point blink / empty seat.
 */
export async function handoffSeat(options: {
  land: () => void;
  drop: () => void;
  token?: number;
  isCurrent?: (token: number) => boolean;
}): Promise<boolean> {
  const { ok } = await runHandoff(
    { land: options.land, drop: options.drop },
    {
      waitFrame: async () => {
        await nextTick();
        await deskFrame();
      },
      cancelled:
        options.token !== undefined && options.isCurrent
          ? () => !options.isCurrent!(options.token!)
          : undefined,
    },
  );
  return ok;
}
