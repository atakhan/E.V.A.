/**
 * Memory constructor mode — draft structure of the agent’s memory organ.
 *
 * Content facets (1–6) and attention (7) sit on a full circle around the
 * memory center. Radius = three icon seats from center to icon center.
 *
 * Achievements/failures appear only when a skill writes them via memory Actions.
 */
import { AGENT_ICON } from "@/features/projects/utils/deskLayout";
import { roundOrbit, type OrbitAnchor, type OrbitBounds } from "@/features/projects/utils/packedOrbit";

/** Same seat size as agent icons on the project desk. */
export const MEMORY_SAT_SIZE = AGENT_ICON;

/** Center-to-center distance: three icon seats from the memory hub. */
export const MEMORY_ORBIT_RADIUS = 3 * MEMORY_SAT_SIZE;

/** How many memory cards may sit in the attention zone at once (draft). */
export const MEMORY_ATTENTION_CAPACITY = 5;

export const MEMORY_ORBIT_ITEMS = [
  {
    id: "self",
    label: "Знание о себе",
    caption: "О себе",
    role: "content" as const,
    shelf: "Знание агента о себе. Пока полка пустая — ждёт куски из навыков и жизни.",
  },
  {
    id: "life",
    label: "История жизни",
    caption: "Жизнь",
    role: "content" as const,
    shelf: "Main log — непрерывная нить жизни агента.",
  },
  {
    id: "outcomes",
    label: "Достижения и провалы",
    caption: "Вехи",
    role: "content" as const,
    shelf:
      "Веха появляется только когда навык сам записывает её Action’ом работы с памятью. Исход прогона сам по себе веху не ставит.",
  },
  {
    id: "tasks",
    label: "Актуальные задачи",
    caption: "Задачи",
    role: "content" as const,
    shelf: "Что сейчас в работе — живой срез, не весь архив.",
  },
  {
    id: "others",
    label: "Знания о других",
    caption: "Другие",
    role: "content" as const,
    shelf: "Агенты и люди: связи, манифест взаимодействия, заметки о других.",
  },
  {
    id: "skills",
    label: "Знания навыков",
    caption: "Навыки",
    role: "content" as const,
    shelf:
      "Куски памяти, которые навык кладёт при установке и читает/пишет в работе. Связь навык ↔ память.",
  },
  {
    id: "focus",
    label: "Зона внимания",
    caption: "Внимание",
    role: "attention" as const,
    shelf: `Ограниченное пространство карточек в фокусе (черновик: до ${MEMORY_ATTENTION_CAPACITY}). Не тип знания — ёмкость сцены.`,
  },
] as const;

export type MemoryOrbitId = (typeof MEMORY_ORBIT_ITEMS)[number]["id"];

export interface MemoryOrbitSlot {
  id: MemoryOrbitId;
  label: string;
  caption: string;
  role: "content" | "attention";
  shelf: string;
  x: number;
  y: number;
}

export function memoryOrbitItem(id: MemoryOrbitId) {
  return MEMORY_ORBIT_ITEMS.find((item) => item.id === id) ?? MEMORY_ORBIT_ITEMS[0]!;
}

/**
 * Icon-box top-left slots on a full circle around the memory center.
 * Even spacing; first seat at the top; radius = three icons.
 */
export function layoutMemoryOrbit(
  anchor: OrbitAnchor,
  _bounds: OrbitBounds,
): MemoryOrbitSlot[] {
  const items = MEMORY_ORBIT_ITEMS;
  const count = items.length;
  if (count === 0) return [];

  return items.map((item, index) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / count;
    const cx = anchor.x + Math.cos(angle) * MEMORY_ORBIT_RADIUS;
    const cy = anchor.y + Math.sin(angle) * MEMORY_ORBIT_RADIUS;
    return {
      ...item,
      x: roundOrbit(cx - MEMORY_SAT_SIZE / 2),
      y: roundOrbit(cy - MEMORY_SAT_SIZE / 2),
    };
  });
}
