<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { DEFAULT_AGENT_ICON } from "@/features/agents/types/agent";
import type { Project } from "@/features/projects/types/project";
import type { Flight } from "@/features/projects/motion";
import { AGENT_ICON, type DeskAnchor } from "@/features/projects/utils/deskLayout";
import { DESK_ASIDE_MS } from "@/features/projects/utils/deskMotion";
import { orbitIconStyle, orbitPlaceStyle } from "@/features/projects/utils/orbitStyles";
import {
  CREATE_PROJECT_SIZE,
  layoutAroundEva,
  layoutCreateAroundEva,
} from "@/features/projects/utils/projectsHubLayout";

const props = withDefaults(
  defineProps<{
    projects: Project[];
    /** Center of the Eva sphere, in desk coordinates. */
    anchor?: DeskAnchor | null;
    focusSlug?: string | null;
    dimmed?: boolean;
    focusHidden?: boolean;
    /**
     * When false, project icons sit collapsed on Eva and then
     * pop out along the arc when flipped to true.
     */
    satellites?: boolean;
    /** Skip transform transition for one frame (snap before flying home). */
    iconSnap?: boolean;
    /** Moves the focused project icon toward Eva / runtime while the project desk catches up. */
    iconFlight?: Flight | null;
    /**
     * Transparent board so the project desk underneath can animate in the same pass
     * as the flying hub icon.
     */
    clearBackdrop?: boolean;
  }>(),
  {
    anchor: null,
    focusSlug: null,
    dimmed: false,
    focusHidden: false,
    satellites: true,
    iconSnap: false,
    iconFlight: null,
    clearBackdrop: false,
  },
);

const emit = defineEmits<{
  open: [project: Project];
  remove: [project: Project];
  create: [];
}>();

const board = ref<HTMLElement | null>(null);
const size = ref({ width: 0, height: 0 });

const bySlug = computed(() => new Map(props.projects.map((project) => [project.slug, project])));

const placed = computed(() => {
  const anchor = props.anchor;
  // Wait for Eva's measured center — otherwise icons stack in the corner.
  if (!anchor || size.value.width <= 0 || size.value.height <= 0) return [];
  return layoutAroundEva(
    props.projects.map((project) => project.slug),
    anchor,
    size.value,
  );
});

/** Inner-orbit create seat — closer to Eva than the packed project ring. */
const createSlot = computed(() => {
  const anchor = props.anchor;
  if (!anchor || size.value.width <= 0 || size.value.height <= 0) return null;
  return layoutCreateAroundEva(anchor, size.value);
});

function projectOf(slug: string): Project | undefined {
  return bySlug.value.get(slug);
}

function measure() {
  const root = board.value;
  if (!root) return;
  size.value = { width: root.clientWidth, height: root.clientHeight };
}

let observer: ResizeObserver | null = null;

onMounted(() => {
  measure();
  observer = new ResizeObserver(measure);
  if (board.value) observer.observe(board.value);
});

onUnmounted(() => {
  observer?.disconnect();
});

watch(
  () => props.anchor,
  () => measure(),
);

function placeStyle(slot: { x: number; y: number; id: string }, _index: number) {
  return orbitPlaceStyle({
    x: slot.x,
    y: slot.y,
    focused: slot.id === props.focusSlug,
    dimmed: props.dimmed,
    satellites: props.satellites,
    anchor: props.anchor,
    // Hub projects stay simultaneous; agent desk keeps cascade via index/count.
    index: 0,
    count: 1,
    clearBackdrop: props.clearBackdrop,
  });
}

function iconStyle(slug: string) {
  return orbitIconStyle({
    slug,
    focusSlug: props.focusSlug,
    iconFlight: props.iconFlight,
    focusHidden: props.focusHidden,
    iconSnap: props.iconSnap,
  });
}

function onOpen(event: MouseEvent, project: Project) {
  if (!(event.target instanceof Element) || event.target.closest("[data-desk-action]")) return;
  emit("open", project);
}

defineExpose({ rootEl: board });
</script>

<template>
  <div
    ref="board"
    data-projects-desk
    class="relative h-full w-full overflow-hidden"
    :class="clearBackdrop ? 'bg-transparent' : 'bg-base-200'"
    :style="
      clearBackdrop
        ? undefined
        : 'background-image: radial-gradient(circle, color-mix(in oklab, var(--color-base-content) 16%, transparent) 1px, transparent 1px); background-size: 22px 22px'
    "
  >
    <p
      v-if="projects.length === 0 && satellites"
      class="pointer-events-none absolute inset-0 flex items-center justify-center px-6 pb-40 text-center text-sm text-base-content/60"
    >
      Пока нет проектов. Нажми «Новый» у Евы — она соберёт стол.
    </p>
    <article
      v-for="(slot, index) in placed"
      :key="slot.id"
      class="group absolute flex w-max max-w-48 cursor-pointer flex-col items-center gap-1.5 text-center motion-reduce:transition-none"
      role="button"
      :data-project="slot.id"
      :aria-label="projectOf(slot.id)?.name ?? slot.id"
      :class="[
        dimmed || !satellites ? 'pointer-events-none' : '',
        slot.id === focusSlug ? 'z-30' : 'z-10',
      ]"
      :style="placeStyle(slot, index)"
      @click="projectOf(slot.id) && onOpen($event, projectOf(slot.id)!)"
    >
      <img
        :src="DEFAULT_AGENT_ICON"
        alt=""
        class="size-16 rounded-full border border-base-300 bg-base-100 object-cover shadow-md"
        :class="slot.id === focusSlug && focusHidden ? 'opacity-0' : 'opacity-100'"
        :style="iconStyle(slot.id)"
      />
      <span
        class="max-w-48 truncate text-sm font-medium leading-tight transition-opacity motion-reduce:transition-none"
        :class="dimmed || !satellites ? 'opacity-0' : 'opacity-100'"
        :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      >
        {{ projectOf(slot.id)?.name ?? slot.id }}
      </span>
      <span
        class="max-w-48 truncate text-xs leading-tight text-base-content/50 transition-opacity motion-reduce:transition-none"
        :class="dimmed || !satellites ? 'opacity-0' : 'opacity-100'"
        :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      >
        {{ projectOf(slot.id)?.agents.length ?? 0 }} на столе
      </span>
      <button
        type="button"
        data-desk-action
        class="btn btn-xs btn-square btn-ghost absolute -right-2 -top-2 border border-base-300 bg-base-100 opacity-0 shadow-sm group-hover:opacity-100"
        aria-label="Удалить проект"
        @pointerdown.stop
        @click.stop="projectOf(slot.id) && emit('remove', projectOf(slot.id)!)"
      >
        ✕
      </button>
    </article>

    <!-- Create: gray seat on Eva’s inner orbit (closer than projects). -->
    <button
      v-if="createSlot"
      type="button"
      data-create-project
      class="absolute z-20 flex flex-col items-center gap-1.5 text-center motion-reduce:transition-none"
      :class="dimmed || !satellites || clearBackdrop ? 'pointer-events-none' : ''"
      :style="placeStyle(createSlot, 0)"
      aria-label="Новый проект"
      title="Новый проект"
      @click="emit('create')"
    >
      <span
        class="flex items-center justify-center rounded-full border-2 border-dashed border-base-content/35 bg-base-300/50 text-base-content/55 shadow-sm transition hover:border-base-content/50 hover:bg-base-300/80 hover:text-base-content/80"
        :style="{ width: `${CREATE_PROJECT_SIZE}px`, height: `${CREATE_PROJECT_SIZE}px` }"
      >
        <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path stroke-linecap="round" d="M12 5v14M5 12h14" />
        </svg>
      </span>
      <span
        class="text-sm font-medium leading-tight text-base-content/55 transition-opacity motion-reduce:transition-none"
        :class="dimmed || !satellites ? 'opacity-0' : 'opacity-100'"
        :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      >Новый</span>
    </button>
  </div>
</template>
