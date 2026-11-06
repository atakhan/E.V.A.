/**
 * Plugin constructor mode — details of a tool instance.
 *
 * Invariant: the plugin card sits in the **left half**, flush toward the midline
 * with a gutter of air; detail facets are a **vertical list** just past that
 * gutter (no spherical orbit). Labels sit to the **right** of each icon.
 * Facet open → same icon+label row flies to the hub (pivot on the glyph); reading
 * stage on the right. Escape only.
 */
import { AGENT_ICON } from "@/features/projects/utils/deskLayout";
import { AGENT_SIZE } from "@/features/constructor/types/constructor";
import { roundOrbit, type OrbitAnchor, type OrbitBounds } from "@/features/projects/utils/packedOrbit";
import type { ToolDefinition } from "@/features/tools/types/tool";

/** Same seat size as memory satellites / agent icons. */
export const PLUGIN_SAT_SIZE = AGENT_ICON;

/** Gap between detail icons in the vertical column. */
export const PLUGIN_COLUMN_GAP = 14;

/**
 * Air between the plugin card’s right edge (left half) and the detail column
 * (starts at the midline + this gutter).
 */
export const PLUGIN_HUB_GUTTER = 36;

/** Side-label type for icons-with-text-to-the-right. */
export const PLUGIN_LABEL_TYPE = "clamp(0.9rem, 0.55vw + 0.7rem, 1.1rem)";

export const PLUGIN_ORBIT_ITEMS = [
  {
    id: "about",
    label: "О плагине",
    caption: "О себе",
    shelf: "Имя instance, тип, статус связи и описание.",
  },
  {
    id: "commands",
    label: "Команды",
    caption: "Команды",
    shelf: "Что умеет плагин — команды каталога и кто их вызывает.",
  },
  {
    id: "events",
    label: "События",
    caption: "События",
    shelf: "События, которые плагин может порождать.",
  },
  {
    id: "config",
    label: "Настройки",
    caption: "Config",
    shelf: "Конфиг instance по схеме типа.",
  },
  {
    id: "credential",
    label: "Учётные данные",
    caption: "Секрет",
    shelf: "Привязка credential, если тип требует секрет.",
  },
  {
    id: "usage",
    label: "Использование",
    caption: "Где",
    shelf: "Actions и skills, которые зовут этот instance.",
  },
] as const;

export type PluginOrbitId = (typeof PLUGIN_ORBIT_ITEMS)[number]["id"];

export interface PluginOrbitSlot {
  id: PluginOrbitId;
  label: string;
  caption: string;
  shelf: string;
  x: number;
  y: number;
}

export function pluginOrbitItem(id: PluginOrbitId) {
  return PLUGIN_ORBIT_ITEMS.find((item) => item.id === id) ?? PLUGIN_ORBIT_ITEMS[0]!;
}

/** Facets for this tool type — drop credential when the type has no credentialKind. */
export function pluginOrbitItemsFor(typeDef: ToolDefinition | undefined | null) {
  const needsCredential = Boolean(typeDef?.credentialKind);
  return PLUGIN_ORBIT_ITEMS.filter((item) => item.id !== "credential" || needsCredential);
}

/**
 * Seat the plugin card in the left half, pressed to the midline with gutter air.
 * `from` is the unscaled card box; scale matches hub icon height (AGENT_SIZE).
 */
export function layoutPluginHubPose(
  bounds: OrbitBounds,
  from: { width: number; height: number },
): { x: number; y: number; width: number; height: number; scale: number } {
  const scale = from.height > 0 ? AGENT_SIZE / from.height : 1;
  const visualW = from.width * scale;
  const midX = bounds.width / 2;
  const midY = bounds.height / 2;
  const centerX = midX - PLUGIN_HUB_GUTTER - visualW / 2;
  return {
    x: roundOrbit(centerX - from.width / 2),
    y: roundOrbit(midY - from.height / 2),
    width: from.width,
    height: from.height,
    scale,
  };
}

/**
 * Icon-box top-left slots: vertical column starting just right of the midline gutter.
 */
export function layoutPluginColumn(
  _anchor: OrbitAnchor,
  bounds: OrbitBounds,
  typeDef?: ToolDefinition | null,
): PluginOrbitSlot[] {
  const items = pluginOrbitItemsFor(typeDef);
  const count = items.length;
  if (count === 0) return [];

  const pitch = PLUGIN_SAT_SIZE + PLUGIN_COLUMN_GAP;
  const midX = bounds.width / 2;
  const midY = bounds.height / 2;
  const colLeft = midX + PLUGIN_HUB_GUTTER;
  const firstCenterY = midY - ((count - 1) * pitch) / 2;

  return items.map((item, index) => {
    const cy = firstCenterY + index * pitch;
    return {
      ...item,
      x: roundOrbit(colLeft),
      y: roundOrbit(cy - PLUGIN_SAT_SIZE / 2),
    };
  });
}

/** @deprecated Use layoutPluginColumn. */
export const layoutPluginOrbit = layoutPluginColumn;
