/**
 * Skill constructor mode — details of one skill.
 *
 * Same spatial layout as plugin mode (reuse, not a third metaphor):
 * skill card in the **left half** against the midline gutter; detail facets a
 * **vertical list** just past that gutter; labels to the **right** of icons.
 * Facet open → icon+label flies to hub; reading stage on the right. Escape only.
 */
import { roundOrbit, type OrbitAnchor, type OrbitBounds } from "@/features/projects/utils/packedOrbit";
import {
  layoutPluginHubPose,
  PLUGIN_COLUMN_GAP,
  PLUGIN_HUB_GUTTER,
  PLUGIN_LABEL_TYPE,
  PLUGIN_SAT_SIZE,
} from "@/features/tools/utils/pluginOrbit";

/** Same seat size / label type as plugin detail column. */
export const SKILL_SAT_SIZE = PLUGIN_SAT_SIZE;
export const SKILL_LABEL_TYPE = PLUGIN_LABEL_TYPE;
export const SKILL_HUB_GUTTER = PLUGIN_HUB_GUTTER;
export const SKILL_COLUMN_GAP = PLUGIN_COLUMN_GAP;

/** Hub pose = plugin hub pose (left half, midline gutter). */
export const layoutSkillHubPose = layoutPluginHubPose;

export const SKILL_ORBIT_ITEMS = [
  {
    id: "about",
    label: "О навыке",
    caption: "О себе",
    shelf: "Имя, описание, версия и метаданные навыка.",
  },
  {
    id: "states",
    label: "Состояния",
    caption: "Состояния",
    shelf: "FSM: initial и список состояний навыка.",
  },
  {
    id: "needs",
    label: "Что нужно",
    caption: "Нужно",
    shelf: "Каналы, плагины и Actions, которые навык вызывает или ждёт.",
  },
] as const;

export type SkillOrbitId = (typeof SKILL_ORBIT_ITEMS)[number]["id"];

export interface SkillOrbitSlot {
  id: SkillOrbitId;
  label: string;
  caption: string;
  shelf: string;
  x: number;
  y: number;
}

export function skillOrbitItem(id: SkillOrbitId) {
  return SKILL_ORBIT_ITEMS.find((item) => item.id === id) ?? SKILL_ORBIT_ITEMS[0]!;
}

/**
 * Icon-box top-left slots: vertical column starting just right of the midline gutter.
 * Same packing as `layoutPluginColumn`.
 */
export function layoutSkillColumn(
  _anchor: OrbitAnchor,
  bounds: OrbitBounds,
): SkillOrbitSlot[] {
  const items = SKILL_ORBIT_ITEMS;
  const count = items.length;
  if (count === 0) return [];

  const pitch = SKILL_SAT_SIZE + SKILL_COLUMN_GAP;
  const midX = bounds.width / 2;
  const midY = bounds.height / 2;
  const colLeft = midX + SKILL_HUB_GUTTER;
  const firstCenterY = midY - ((count - 1) * pitch) / 2;

  return items.map((item, index) => {
    const cy = firstCenterY + index * pitch;
    return {
      ...item,
      x: roundOrbit(colLeft),
      y: roundOrbit(cy - SKILL_SAT_SIZE / 2),
    };
  });
}
