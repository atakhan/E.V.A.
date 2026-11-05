<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import { fetchAgent } from "@/features/agents/services/agentsApi";
import { forgetAgent, getAgentBySlug, rememberAgent } from "@/features/agents/services/agentsStorage";
import { DEFAULT_AGENT_ICON, type Agent } from "@/features/agents/types/agent";
import { AGENT_SIZE } from "@/features/constructor/types/constructor";
import { describeAgentHub } from "@/features/constructor/utils/agentHubStatus";
import ConstructorView from "@/features/constructor/views/ConstructorView.vue";
import ProjectDesk from "@/features/projects/components/ProjectDesk.vue";
import ProjectFormDialog from "@/features/projects/components/ProjectFormDialog.vue";
import { useProjects } from "@/features/projects/composables/useProjects";
import type { Project, ProjectAgent } from "@/features/projects/types/project";
import { AGENT_ICON, type DeskAnchor } from "@/features/projects/utils/deskLayout";
import {
  DESK_ASIDE_MS,
  DESK_EASE,
  DESK_EASE_OPEN,
  DESK_HANDOFF_MS,
  DESK_MOVE_MS,
} from "@/features/projects/utils/deskMotion";
import { useRuntimeSummary } from "@/features/runtime/composables/useRuntimeSummary";
import { projectAgentPath, projectPath, projectsPath } from "@/router/paths";
import { appNavItems, isAppNavActive } from "@/shared/layout/appNav";

const props = defineProps<{
  projectSlug: string;
  agentSlug?: string;
}>();

type EdgePanel = "nav" | "library";
type DeskStage = "project" | "entering" | "agent";

const route = useRoute();
const router = useRouter();
const { libraryAgents } = useAgents();
const { fetchProject, saveAgents, removeProject } = useProjects();
const { summary } = useRuntimeSummary();

const project = ref<Project | null>(null);
const memberAgents = ref<Agent[]>([]);
const loadError = ref<string | null>(null);
const panel = ref<EdgePanel | null>(null);
const editDialog = useTemplateRef("editDialog");
const runtimeAnchor = useTemplateRef<HTMLButtonElement>("runtimeAnchor");
const deskAnchor = ref<DeskAnchor | null>(null);
const deskSize = ref({ width: 0, height: 0 });

const openedSlug = props.agentSlug || null;
const focusSlug = ref<string | null>(openedSlug);
const dimmed = ref(Boolean(openedSlug));
const focusHidden = ref(Boolean(openedSlug));
const constructorOn = ref(Boolean(openedSlug));
const hubVisible = ref(false);
const satellites = ref(false);
const stage = ref<DeskStage>(openedSlug ? "agent" : "project");
const bootPan = ref<{ x: number; y: number } | null>(null);
const glyphScale = ref(1);
const glide = ref(false);
const glideEase = ref(DESK_EASE);
const glideMs = ref(DESK_MOVE_MS);
const glideDelay = ref(0);
const glideTo = ref<{ x: number; y: number } | null>(null);
const worldAt = ref<{ x: number; y: number } | null>(null);
const showMeta = ref(Boolean(openedSlug));
const iconFlight = ref<{ dx: number; dy: number; scale: number } | null>(null);
let settleOnReady = Boolean(openedSlug);
let motion = 0;
let readyWait: (() => void) | null = null;

const edgeButtonClass =
  "btn border border-base-300/60 bg-base-100/90 shadow-lg backdrop-blur-sm transition-[opacity,transform] motion-reduce:transition-none";

const chromeClass = computed(() =>
  dimmed.value ? "z-10 opacity-30 pointer-events-none" : "z-40 opacity-100",
);

const chromeStyle = { transitionDuration: `${DESK_ASIDE_MS}ms` };

const memberSlugs = computed(() => new Set(project.value?.agents.map((agent) => agent.agentSlug) ?? []));

const placedOrigins = computed(() => {
  const origins = new Set<string>();
  for (const member of project.value?.agents ?? []) {
    origins.add(member.originSlug || member.agentSlug);
  }
  return origins;
});

const availableAgents = computed(() =>
  libraryAgents.value.filter((agent) => !placedOrigins.value.has(agent.slug)),
);

const deskAgents = computed(() => {
  const known = new Map(libraryAgents.value.map((agent) => [agent.slug, agent]));
  for (const agent of memberAgents.value) known.set(agent.slug, agent);
  return [...known.values()];
});

const memberSummaries = computed(() =>
  (summary.value?.agents ?? []).filter((agent) => memberSlugs.value.has(agent.agentSlug)),
);

const totals = computed(() =>
  memberSummaries.value.reduce(
    (acc, agent) => {
      acc.running += agent.running;
      acc.waiting += agent.waiting;
      acc.error += agent.error;
      return acc;
    },
    { running: 0, waiting: 0, error: 0 },
  ),
);

const statusBySlug = computed(() => {
  const summaries = new Map((summary.value?.agents ?? []).map((agent) => [agent.agentSlug, agent]));
    const known = new Set([
      ...libraryAgents.value.map((agent) => agent.slug),
      ...memberAgents.value.map((agent) => agent.slug),
    ]);
  const lines: Record<string, string> = {};
  for (const member of project.value?.agents ?? []) {
    const agentSummary = summaries.get(member.agentSlug);
    if (agentSummary) {
      lines[member.agentSlug] = describeAgentHub(agentSummary).compactLine;
    } else if (!known.has(member.agentSlug)) {
      lines[member.agentSlug] = "нет в библиотеке";
    }
  }
  return lines;
});

const runtimeFocused = computed(
  () => Boolean(focusSlug.value) && focusSlug.value === project.value?.runtimeAgentSlug,
);

const runtimeClass = computed(() => {
  if (runtimeFocused.value && focusHidden.value) return "pointer-events-none opacity-0";
  if (dimmed.value && !runtimeFocused.value) return "pointer-events-none opacity-30";
  return "opacity-100";
});

const runtimeStyle = computed(() => {
  const handoff = runtimeFocused.value && focusHidden.value;
  const parked = dimmed.value && !runtimeFocused.value;
  return {
    transform: `translateX(-50%) scale(${parked ? 0.86 : 1})`,
    transition: handoff ? "none" : `opacity ${DESK_ASIDE_MS}ms, transform ${DESK_ASIDE_MS}ms`,
    zIndex: dimmed.value && !runtimeFocused.value ? 25 : 40,
    outline: "none",
  };
});

const runtimeLine = computed(() => {
  const parts: string[] = [];
  if (totals.value.running) parts.push(`идут ${totals.value.running}`);
  if (totals.value.waiting) parts.push(`ждут ${totals.value.waiting}`);
  if (totals.value.error) parts.push(`ошибок ${totals.value.error}`);
  return parts.length ? parts.join(" · ") : "тихо";
});

function togglePanel(next: EdgePanel) {
  panel.value = panel.value === next ? null : next;
}

function openProjectEdit() {
  panel.value = null;
  editDialog.value?.open();
}

async function onProjectSaved(next: Project) {
  project.value = next;
  const runtimeSlug = next.runtimeAgentSlug;
  if (!runtimeSlug) return;
  try {
    rememberAgent(await fetchAgent(runtimeSlug));
  } catch {
    const cached = getAgentBySlug(runtimeSlug);
    if (cached) rememberAgent({ ...cached, name: next.name });
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  if (document.querySelector("[data-channel-mode]")) return;
  if (panel.value) {
    panel.value = null;
    return;
  }
  const target = event.target;
  if (target instanceof HTMLElement && target.closest("input, textarea, select, [contenteditable='true']")) {
    return;
  }
  if (stage.value !== "project") {
    event.preventDefault();
    void backToProject();
  }
}

async function rememberMembers() {
  if (!project.value) {
    memberAgents.value = [];
    return;
  }
  const loaded: Agent[] = [];
  for (const member of project.value.agents) {
    try {
      const agent = await fetchAgent(member.agentSlug);
      rememberAgent(agent);
      loaded.push(getAgentBySlug(member.agentSlug) ?? agent);
    } catch {
      const cached = getAgentBySlug(member.agentSlug);
      if (cached) loaded.push(cached);
    }
  }
  memberAgents.value = loaded;
}

async function loadProject() {
  loadError.value = null;
  try {
    project.value = await fetchProject(props.projectSlug);
    const opened = props.agentSlug;
    const redirected = project.value.agents.find(
      (member) => member.originSlug === opened && member.agentSlug !== opened,
    );
    if (opened && redirected) {
      await router.replace(projectAgentPath(props.projectSlug, redirected.agentSlug));
    }
    await rememberMembers();
    const runtimeSlug = project.value.runtimeAgentSlug;
    if (runtimeSlug && !getAgentBySlug(runtimeSlug)) {
      rememberAgent(await fetchAgent(runtimeSlug));
    }
  } catch (error) {
    project.value = null;
    memberAgents.value = [];
    loadError.value = error instanceof Error ? error.message : "Проект не найден";
  }
}

function measureRuntime() {
  const button = runtimeAnchor.value;
  const desk = document.querySelector("[data-project-desk]");
  const icon = button?.querySelector("img");
  if (!button || !desk || !icon) return;
  const iconRect = icon.getBoundingClientRect();
  const deskRect = desk.getBoundingClientRect();
  deskAnchor.value = {
    x: Math.round((iconRect.left + iconRect.width / 2 - deskRect.left) * 10) / 10,
    y: Math.round((iconRect.top + iconRect.height / 2 - deskRect.top) * 10) / 10,
  };
  deskSize.value = { width: desk.clientWidth, height: desk.clientHeight };
}

watch(project, () => {
  void nextTick(measureRuntime);
});

let anchorObserver: ResizeObserver | null = null;

onMounted(() => {
  void loadProject();
  document.addEventListener("keydown", onKeydown);
  measureRuntime();
  anchorObserver = new ResizeObserver(measureRuntime);
  anchorObserver.observe(document.documentElement);
});

onUnmounted(() => {
  motion += 1;
  releaseReady();
  document.removeEventListener("keydown", onKeydown);
  anchorObserver?.disconnect();
});

watch(
  () => props.projectSlug,
  () => {
    void loadProject();
  },
);

async function persist(agents: ProjectAgent[]) {
  if (!project.value) return;
  project.value = { ...project.value, agents };
  project.value = await saveAgents(project.value.slug, agents);
}

async function onArrange(agents: ProjectAgent[]) {
  if (!project.value) return;
  await persist(agents);
}

async function connectAgent(agentSlug: string) {
  if (!project.value) return;
  panel.value = null;
  await persist([...project.value.agents, { agentSlug, x: 0, y: 0 }]);
  await rememberMembers();
}

async function removeAgent(agentSlug: string) {
  if (!project.value) return;
  await persist(project.value.agents.filter((agent) => agent.agentSlug !== agentSlug));
  forgetAgent(agentSlug);
  memberAgents.value = memberAgents.value.filter((agent) => agent.slug !== agentSlug);
}

async function openAgent(agentSlug: string) {
  if (stage.value !== "project") return;
  panel.value = null;
  await router.push(projectAgentPath(props.projectSlug, agentSlug));
}

function blurRuntime() {
  const button = runtimeAnchor.value;
  if (button && document.activeElement === button) button.blur();
}

async function openRuntime() {
  const slug = project.value?.runtimeAgentSlug;
  if (!slug) return;
  blurRuntime();
  if (!getAgentBySlug(slug)) {
    rememberAgent(await fetchAgent(slug));
  }
  await openAgent(slug);
}

async function backToProject() {
  if (stage.value === "project") return;
  await router.push(projectPath(props.projectSlug));
}

function reducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function wait(ms: number): Promise<void> {
  if (reducedMotion()) return Promise.resolve();
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function frame(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => resolve());
  });
}

function deskCenter(): { x: number; y: number } {
  return { x: deskSize.value.width / 2, y: deskSize.value.height / 2 };
}

function measureFocus(): { x: number; y: number; width: number } | null {
  const slug = focusSlug.value;
  const desk = document.querySelector("[data-project-desk]");
  if (!slug || !desk) return null;
  const img =
    desk.querySelector(`[data-agent="${CSS.escape(slug)}"] img`) ??
    document.querySelector(`[data-agent="${CSS.escape(slug)}"] img`);
  if (!(img instanceof HTMLElement)) return null;
  const deskRect = desk.getBoundingClientRect();
  const rect = img.getBoundingClientRect();
  return {
    x: rect.left + rect.width / 2 - deskRect.left,
    y: rect.top + rect.height / 2 - deskRect.top,
    width: rect.width,
  };
}

function releaseReady() {
  const resolve = readyWait;
  readyWait = null;
  resolve?.();
}

function onConstructorReady() {
  if (settleOnReady) {
    settleOnReady = false;
    hubVisible.value = true;
    window.setTimeout(() => {
      if (stage.value === "agent") satellites.value = true;
    }, reducedMotion() ? 0 : DESK_HANDOFF_MS);
  }
  releaseReady();
}

function waitForConstructor(): Promise<void> {
  return new Promise((resolve) => {
    const timer = window.setTimeout(resolve, 800);
    readyWait = () => {
      window.clearTimeout(timer);
      resolve();
    };
  });
}

async function enter(slug: string) {
  if (stage.value !== "project") {
    focusSlug.value = slug;
    return;
  }
  const token = ++motion;
  settleOnReady = false;
  focusSlug.value = slug;
  stage.value = "entering";
  panel.value = null;
  dimmed.value = true;
  focusHidden.value = false;
  satellites.value = false;
  hubVisible.value = false;
  constructorOn.value = false;
  glide.value = false;
  glideTo.value = null;
  showMeta.value = false;

  if (reducedMotion()) {
    measureRuntime();
    bootPan.value = deskCenter();
    glyphScale.value = 1;
    focusHidden.value = true;
    hubVisible.value = true;
    satellites.value = true;
    showMeta.value = true;
    constructorOn.value = true;
    stage.value = "agent";
    return;
  }

  measureRuntime();
  const start = measureFocus() ?? deskCenter();
  const center = deskCenter();
  iconFlight.value = {
    dx: center.x - start.x,
    dy: center.y - start.y,
    scale: AGENT_SIZE / AGENT_ICON,
  };
  bootPan.value = start;
  glyphScale.value = AGENT_ICON / AGENT_SIZE;
  hubVisible.value = false;
  glideDelay.value = 0;
  glideMs.value = DESK_MOVE_MS;
  await nextTick();
  await frame();
  await frame();
  if (token !== motion) return;
  const flightStarted = performance.now();
  const ready = waitForConstructor();
  constructorOn.value = true;
  await ready;
  if (token !== motion) return;
  const here = measureFocus();
  const elapsed = Math.min(DESK_MOVE_MS, Math.max(0, performance.now() - flightStarted));
  const remain = Math.max(0, DESK_MOVE_MS - elapsed);
  if (here) {
    bootPan.value = { x: here.x, y: here.y };
    glyphScale.value = here.width > 0 ? here.width / AGENT_SIZE : 1;
  }
  await nextTick();
  await frame();
  if (token !== motion) return;
  hubVisible.value = true;
  focusHidden.value = true;
  iconFlight.value = null;
  showMeta.value = true;
  satellites.value = true;
  if (remain < 48) {
    bootPan.value = center;
    glyphScale.value = 1;
    worldAt.value = center;
    stage.value = "agent";
    return;
  }
  glideMs.value = remain;
  glideEase.value = DESK_EASE_OPEN;
  glide.value = true;
  await nextTick();
  await frame();
  if (token !== motion) return;
  glyphScale.value = 1;
  glideTo.value = center;
  await wait(remain);
  if (token !== motion) return;
  glide.value = false;
  glideDelay.value = 0;
  glideMs.value = DESK_MOVE_MS;
  worldAt.value = center;
  await nextTick();
  if (token !== motion) return;
  stage.value = "agent";
}

async function leave() {
  if (stage.value === "project") return;
  blurRuntime();
  const token = ++motion;
  settleOnReady = false;
  releaseReady();

  if (reducedMotion()) {
    constructorOn.value = false;
    satellites.value = false;
    hubVisible.value = false;
    focusHidden.value = false;
    dimmed.value = false;
    focusSlug.value = null;
    glide.value = false;
    glideTo.value = null;
    glyphScale.value = 1;
    stage.value = "project";
    return;
  }

  const fadeSatellites = satellites.value;
  showMeta.value = false;
  if (!focusHidden.value) {
    iconFlight.value = null;
    dimmed.value = false;
    satellites.value = false;
    constructorOn.value = false;
    hubVisible.value = false;
    focusSlug.value = null;
    glide.value = false;
    glideDelay.value = 0;
    glideTo.value = null;
    glyphScale.value = 1;
    stage.value = "project";
    return;
  }
  const hideConstructor = constructorOn.value;
  if (hideConstructor) {
    const slot = measureFocus();
    glideEase.value = DESK_EASE;
    glideDelay.value = 0;
    glideMs.value = DESK_MOVE_MS;
    glide.value = true;
    await nextTick();
    await frame();
    if (token !== motion) return;
    if (slot) {
      glyphScale.value = AGENT_ICON / AGENT_SIZE;
      glideTo.value = slot;
    }
    if (fadeSatellites) satellites.value = false;
    dimmed.value = false;
    await wait(slot ? DESK_MOVE_MS : 0);
    if (token !== motion) return;
    focusHidden.value = false;
    hubVisible.value = false;
    await nextTick();
    if (token !== motion) return;
    constructorOn.value = false;
  } else {
    dimmed.value = false;
  }
  blurRuntime();
  focusHidden.value = false;
  focusSlug.value = null;
  glide.value = false;
  glideTo.value = null;
  glyphScale.value = 1;
  stage.value = "project";
}

watch(
  () => props.agentSlug || null,
  (slug) => {
    if (slug) void enter(slug);
    else void leave();
  },
);

async function remove() {
  if (!project.value) return;
  if (!confirm(`Удалить проект «${project.value.name}»? Агенты останутся в библиотеке.`)) return;
  const runtimeSlug = project.value.runtimeAgentSlug;
  const memberSlugsOnDesk = project.value.agents.map((agent) => agent.agentSlug);
  await removeProject(project.value.slug);
  if (runtimeSlug) forgetAgent(runtimeSlug);
  for (const memberSlug of memberSlugsOnDesk) forgetAgent(memberSlug);
  await router.push(projectsPath());
}
</script>

<template>
  <div class="relative h-full min-h-0 w-full overflow-hidden">
    <ProjectDesk
      v-if="project"
      class="h-full"
      :class="dimmed ? 'z-20' : 'z-0'"
      :agents="project.agents"
      :library="deskAgents"
      :status-by-slug="statusBySlug"
      :anchor="deskAnchor"
      :focus-slug="focusSlug"
      :dimmed="dimmed"
      :focus-hidden="focusHidden"
      :icon-flight="iconFlight"
      @open="openAgent"
      @remove="removeAgent"
      @arrange="onArrange"
    />
    <div v-if="constructorOn && focusSlug" class="absolute inset-0 z-30">
      <ConstructorView
        class="h-full"
        :agent-slug="focusSlug"
        :boot-pan="bootPan"
        :satellites-visible="satellites"
        clear-backdrop
        :hub-visible="hubVisible"
        :glyph-scale="glyphScale"
        :glide="glide"
        :glide-ease="glideEase"
        :glide-ms="glideMs"
        :glide-delay="glideDelay"
        :glide-to="glideTo"
        :world-at="worldAt"
        :show-meta="showMeta"
        :project="project"
        @ready="onConstructorReady"
      />
      <button
        type="button"
        :class="[
          edgeButtonClass,
          'absolute top-4 left-[4.25rem] z-40 h-11',
          hubVisible && satellites ? 'opacity-100' : 'pointer-events-none opacity-0',
        ]"
        :style="chromeStyle"
        @click="backToProject"
      >
        К проекту
      </button>
    </div>
    <div
      v-if="!project"
      class="flex h-full items-center justify-center bg-base-200 px-6 text-center"
      style="background-image: radial-gradient(circle, color-mix(in oklab, var(--color-base-content) 16%, transparent) 1px, transparent 1px); background-size: 22px 22px"
    >
      <div v-if="loadError">
        <p class="text-sm text-base-content/70">{{ loadError }}</p>
        <RouterLink :to="projectsPath()" class="btn btn-sm mt-4">К проектам</RouterLink>
      </div>
    </div>

    <button
      type="button"
      :class="[edgeButtonClass, chromeClass, 'fixed top-4 left-[4.25rem] h-11']"
      :style="chromeStyle"
      :aria-expanded="panel === 'nav'"
      @click="togglePanel('nav')"
    >
      Меню
    </button>

    <button
      v-if="project"
      type="button"
      :class="[edgeButtonClass, chromeClass, 'btn-circle btn-md fixed bottom-4 left-4']"
      :style="chromeStyle"
      aria-label="Подключить агента"
      :aria-expanded="panel === 'library'"
      @click="togglePanel('library')"
    >
      <svg viewBox="0 0 24 24" class="size-5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" d="M12 5v14M5 12h14" />
      </svg>
    </button>

    <aside
      v-if="panel === 'nav'"
      class="fixed left-[4.25rem] top-20 z-30 w-64 rounded-2xl border border-base-300 bg-base-100 p-2 shadow-xl"
    >
      <ul class="menu w-full">
        <li v-for="item in appNavItems" :key="item.id">
          <RouterLink
            :to="item.to"
            :class="{ 'menu-active': isAppNavActive(item, route) }"
            :aria-current="isAppNavActive(item, route) ? 'page' : undefined"
          >
            {{ item.label }}
          </RouterLink>
        </li>
      </ul>
      <div v-if="project" class="mt-2 border-t border-base-300 px-2 pt-2">
        <p class="truncate px-2 text-sm font-medium">{{ project.name }}</p>
        <p class="mt-0.5 truncate px-2 font-mono text-xs text-base-content/50">{{ projectPath(project.slug) }}</p>
        <p class="mt-2 px-2 text-xs text-base-content/60">{{ project.description || "Без описания" }}</p>
        <div class="mt-3 flex justify-end gap-2 px-1 pb-1">
          <button type="button" class="btn btn-sm btn-ghost text-error" @click="remove">Удалить</button>
          <button type="button" class="btn btn-sm" @click="openProjectEdit">Править</button>
        </div>
      </div>
    </aside>

    <button
      v-if="project"
      type="button"
      ref="runtimeAnchor"
      :class="[
        runtimeClass,
        'fixed bottom-6 left-1/2 flex w-max max-w-48 flex-col items-center gap-1.5 text-center outline-none focus:outline-none focus-visible:outline-none motion-reduce:transition-none',
      ]"
      :style="runtimeStyle"
      :data-agent="project.runtimeAgentSlug || undefined"
      :aria-label="`Проект ${project.name}`"
      @click="openRuntime"
    >
      <img
        :src="DEFAULT_AGENT_ICON"
        alt=""
        class="size-24 rounded-full border border-base-300 bg-base-100 object-cover shadow-lg"
      />
      <span class="max-w-48 truncate text-sm font-medium leading-tight">{{ project.name }}</span>
      <span class="text-xs leading-tight text-base-content/50">{{ runtimeLine }}</span>
    </button>

    <aside
      v-if="panel === 'library' && project"
      class="fixed bottom-64 left-4 z-30 flex max-h-[min(24rem,calc(100vh-18rem))] w-72 flex-col overflow-hidden rounded-2xl border border-base-300 bg-base-100 shadow-xl"
    >
      <header class="border-b border-base-300 px-4 py-3">
        <h2 class="text-base font-semibold">Подключить агента</h2>
        <p class="mt-0.5 text-xs text-base-content/50">Из библиотеки</p>
      </header>
      <ul v-if="availableAgents.length" class="menu min-h-0 w-full flex-1 overflow-y-auto">
        <li v-for="agent in availableAgents" :key="agent.id">
          <button type="button" class="justify-between" @click="connectAgent(agent.slug)">
            <span class="truncate">{{ agent.name }}</span>
            <span class="font-mono text-xs text-base-content/50">/{{ agent.slug }}</span>
          </button>
        </li>
      </ul>
      <p v-else class="px-4 py-6 text-sm text-base-content/60">Все агенты библиотеки уже на столе.</p>
    </aside>

    <ProjectFormDialog
      ref="editDialog"
      mode="edit"
      :project="project"
      @saved="onProjectSaved"
    />
  </div>
</template>
