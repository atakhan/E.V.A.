/**
 * Reading stage — right half of the constructor viewport for detail content.
 *
 * Geometry: Van de Graaf / Tschichold ninths on the half-screen as a recto page
 * (inner 1/9, outer 2/9 of stage width; top 1/9, bottom 2/9 of viewport height).
 *
 * Future: allowlisted content only (typography, forms, motion) — see
 * docs/06-experiments/constructor-reading-stage-draft.md
 */

/** Stage occupies the right half of the viewport. */
export const READING_STAGE_WIDTH = "50vw";

/**
 * Book margins for content inside the stage (recto: outer = screen right edge).
 * Percentages are of the stage box for inline; block uses viewport height via CSS.
 */
export const READING_STAGE_PAD = {
  /** Toward desk center — 1/9 of stage width. */
  inlineStart: "calc(100% / 9)",
  /** Screen right — 2/9 of stage width. */
  inlineEnd: "calc(200% / 9)",
  /** Top — 1/9 of viewport height. */
  blockStart: "calc(100vh / 9)",
  /** Bottom — 2/9 of viewport height. */
  blockEnd: "calc(200vh / 9)",
} as const;

/** Adaptive type scale for the reading stage (viewport-relative). */
export const READING_STAGE_TYPE = {
  eyebrow: "clamp(0.8rem, 0.55vw + 0.65rem, 1rem)",
  body: "clamp(1.05rem, 0.9vw + 0.75rem, 1.35rem)",
  mono: "clamp(0.9rem, 0.7vw + 0.65rem, 1.15rem)",
  label: "clamp(0.85rem, 0.6vw + 0.65rem, 1.05rem)",
} as const;
