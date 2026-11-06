import { AGENT_ICON } from "@/features/projects/utils/deskLayout";
import {
  DESK_EASE,
  DESK_EASE_OPEN,
  DESK_MOVE_MS,
  DESK_REVEAL_MS,
} from "@/features/projects/utils/deskMotion";
import type { Flight } from "@/features/projects/motion/types";

export const BURST_STAGGER_MS = 32;
export const BURST_STAGGER_CAP_MS = 200;

export function prefersReducedOrbitMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function orbitTransition(
  ease: string,
  delayMs: number,
): { transition: string; transitionDelay: string } {
  if (prefersReducedOrbitMotion()) {
    return { transition: "none", transitionDelay: "0ms" };
  }
  return {
    transition: [
      `left ${DESK_REVEAL_MS}ms ${ease}`,
      `top ${DESK_REVEAL_MS}ms ${ease}`,
      `transform ${DESK_REVEAL_MS}ms ${ease}`,
      `opacity ${Math.round(DESK_REVEAL_MS * 0.7)}ms ease`,
    ].join(", "),
    transitionDelay: `${delayMs}ms`,
  };
}

export function burstDelay(index: number, last: number, collapsed: boolean): number {
  return collapsed
    ? Math.min((last - index) * BURST_STAGGER_MS, BURST_STAGGER_CAP_MS)
    : Math.min(index * BURST_STAGGER_MS, BURST_STAGGER_CAP_MS);
}

export type OrbitPlaceInput = {
  x: number;
  y: number;
  focused: boolean;
  dimmed: boolean;
  satellites: boolean;
  anchor: { x: number; y: number } | null | undefined;
  /** When true, first collapsed paint snaps (no transition into the anchor). */
  snapCollapse?: boolean;
  /** Cascade index; omit or use 0 for simultaneous. */
  index?: number;
  count?: number;
  /** Hide non-focus while a clear hub overlays the desk. */
  clearBackdrop?: boolean;
};

export function orbitPlaceStyle(input: OrbitPlaceInput): Record<string, string | number> {
  const focused = input.focused;
  const aside = input.dimmed && !focused;
  const collapsed = !input.satellites && !focused;
  const ease = collapsed ? DESK_EASE : DESK_EASE_OPEN;
  const last = Math.max(0, (input.count ?? 1) - 1);
  const delay = burstDelay(input.index ?? 0, last, collapsed);

  if (collapsed) {
    if (!input.anchor) {
      return {
        left: "50%",
        top: "100%",
        transform: "translateX(-50%) scale(0.15)",
        opacity: "0",
        transition: "none",
        transitionDelay: "0ms",
        zIndex: 10,
      };
    }
    const motion = input.snapCollapse
      ? { transition: "none", transitionDelay: "0ms" }
      : orbitTransition(ease, delay);
    return {
      left: `${input.anchor.x}px`,
      top: `${input.anchor.y - AGENT_ICON / 2}px`,
      transform: "translateX(-50%) scale(0.15)",
      opacity: "0",
      ...motion,
      zIndex: aside ? 10 : 20,
    };
  }

  return {
    left: `${input.x}px`,
    top: `${input.y}px`,
    transform: aside ? "translateX(-50%) scale(0.86)" : "translateX(-50%) scale(1)",
    opacity:
      input.clearBackdrop && !focused
        ? "0"
        : input.dimmed && !focused
          ? "0.3"
          : "1",
    ...orbitTransition(ease, delay),
    zIndex: focused ? 30 : 10,
  };
}

export function orbitIconStyle(options: {
  slug: string;
  focusSlug: string | null | undefined;
  iconFlight: Flight | null | undefined;
  focusHidden?: boolean;
  iconSnap?: boolean;
}): { transform: string; transition: string } {
  const flying = Boolean(options.iconFlight && options.slug === options.focusSlug);
  return {
    transform: flying
      ? `translate(${options.iconFlight!.dx}px, ${options.iconFlight!.dy}px) scale(${options.iconFlight!.scale})`
      : "none",
    transition:
      options.iconSnap || options.focusHidden
        ? "none"
        : `transform ${DESK_MOVE_MS}ms ${DESK_EASE_OPEN}`,
  };
}
