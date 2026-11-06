<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { agentIconSrc } from "@/features/agents/types/agent";
import type { Agent } from "@/features/agents/types/agent";
import type { ProjectAgent } from "@/features/projects/types/project";
import type { Flight } from "@/features/projects/motion";
import { layoutAroundRuntime, type DeskAnchor } from "@/features/projects/utils/deskLayout";
import { DESK_ASIDE_MS } from "@/features/projects/utils/deskMotion";
import { orbitIconStyle, orbitPlaceStyle } from "@/features/projects/utils/orbitStyles";

const props = withDefaults(
  defineProps<{
    agents: ProjectAgent[];
    library: Agent[];
    statusBySlug?: Record<string, string>;
    /** Center of the runtime sphere, in desk coordinates. */
    anchor?: DeskAnchor | null;
    focusSlug?: string | null;
    dimmed?: boolean;
    focusHidden?: boolean;
    /**
     * When false, member icons sit collapsed on the runtime and then
     * pop out along the arc when flipped to true.
     */
    satellites?: boolean;
    /** Moves the focused desk icon toward the agent hub while the constructor catches up. */
    iconFlight?: Flight | null;
  }>(),
  {
    statusBySlug: undefined,
    anchor: null,
    focusSlug: null,
    dimmed: false,
    focusHidden: false,
    satellites: true,
    iconFlight: null,
  },
);

const emit = defineEmits<{
  open: [agentSlug: string];
  remove: [agentSlug: string];
  arrange: [agents: ProjectAgent[]];
}>();

const board = ref<HTMLElement | null>(null);
const size = ref({ width: 0, height: 0 });
/**
 * Until the first expand, collapsed poses snap with no transition so agents never
 * paint on the orbit first and then jerk into the runtime.
 */
const everRevealed = ref(props.satellites);

const bySlug = computed(() => new Map(props.library.map((agent) => [agent.slug, agent])));

const placed = computed(() => {
  const anchor = props.anchor;
  if (!anchor || size.value.width <= 0) return props.agents;
  return layoutAroundRuntime(props.agents, anchor, size.value);
});

let arrangeTimer = 0;

watch(
  () => props.satellites,
  (on) => {
    if (on) everRevealed.value = true;
  },
);

watch(placed, (next) => {
  if (!props.anchor || size.value.width <= 0 || !props.satellites) return;
  if (samePlaces(next, props.agents)) return;
  window.clearTimeout(arrangeTimer);
  arrangeTimer = window.setTimeout(() => emit("arrange", next), 80);
});

function samePlaces(next: ProjectAgent[], current: ProjectAgent[]): boolean {
  if (next.length !== current.length) return false;
  return next.every((agent, index) => {
    const previous = current[index];
    return (
      previous?.agentSlug === agent.agentSlug &&
      previous.x === agent.x &&
      previous.y === agent.y
    );
  });
}

function label(slug: string): string {
  return bySlug.value.get(slug)?.name ?? slug;
}

function status(slug: string): string {
  return props.statusBySlug?.[slug] ?? "";
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
  window.clearTimeout(arrangeTimer);
});

function placeStyle(agent: ProjectAgent & { x: number; y: number }, index: number) {
  return orbitPlaceStyle({
    x: agent.x,
    y: agent.y,
    focused: agent.agentSlug === props.focusSlug,
    dimmed: props.dimmed,
    satellites: props.satellites,
    anchor: props.anchor,
    snapCollapse: !everRevealed.value,
    index,
    count: props.agents.length,
  });
}

function iconStyle(slug: string) {
  return orbitIconStyle({
    slug,
    focusSlug: props.focusSlug,
    iconFlight: props.iconFlight,
    focusHidden: props.focusHidden,
  });
}

function onOpen(event: MouseEvent, agent: ProjectAgent) {
  if (!(event.target instanceof Element) || event.target.closest("[data-desk-action]")) return;
  emit("open", agent.agentSlug);
}

defineExpose({ rootEl: board });
</script>

<template>
  <div
    ref="board"
    data-project-desk
    class="relative h-full w-full overflow-hidden bg-base-200"
    style="background-image: radial-gradient(circle, color-mix(in oklab, var(--color-base-content) 16%, transparent) 1px, transparent 1px); background-size: 22px 22px"
  >
    <p
      v-if="agents.length === 0 && satellites"
      class="pointer-events-none absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-base-content/60"
    >
      На столе пока никого нет. Подключите агента из библиотеки.
    </p>
    <article
      v-for="(agent, index) in placed"
      :key="agent.agentSlug"
      class="group absolute flex w-max max-w-48 cursor-pointer flex-col items-center gap-1.5 text-center motion-reduce:transition-none"
      role="button"
      :data-agent="agent.agentSlug"
      :aria-label="label(agent.agentSlug)"
      :class="[
        dimmed || !satellites ? 'pointer-events-none' : '',
        agent.agentSlug === focusSlug ? 'z-30' : 'z-10',
      ]"
      :style="placeStyle(agent, index)"
      @click="onOpen($event, agent)"
    >
      <img
        :src="agentIconSrc(bySlug.get(agent.agentSlug) ?? { icon: '' })"
        alt=""
        class="size-16 rounded-full border border-base-300 bg-base-100 object-cover shadow-md"
        :class="agent.agentSlug === focusSlug && focusHidden ? 'opacity-0' : 'opacity-100'"
        :style="iconStyle(agent.agentSlug)"
      />
      <span
        class="text-sm font-medium leading-tight break-words transition-opacity motion-reduce:transition-none"
        :class="dimmed || !satellites ? 'opacity-0' : 'opacity-100'"
        :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      >{{ label(agent.agentSlug) }}</span>
      <span
        v-if="status(agent.agentSlug)"
        class="text-xs leading-tight text-base-content/50 transition-opacity motion-reduce:transition-none"
        :class="dimmed || !satellites ? 'opacity-0' : 'opacity-100'"
        :style="{ transitionDuration: `${DESK_ASIDE_MS}ms` }"
      >
        {{ status(agent.agentSlug) }}
      </span>
      <button
        type="button"
        data-desk-action
        class="btn btn-xs btn-square btn-ghost absolute -right-2 -top-2 border border-base-300 bg-base-100 opacity-0 shadow-sm group-hover:opacity-100"
        aria-label="Убрать со стола"
        @pointerdown.stop
        @click.stop="emit('remove', agent.agentSlug)"
      >
        ✕
      </button>
    </article>
  </div>
</template>
