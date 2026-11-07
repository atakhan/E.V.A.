<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";
import { useRouter } from "vue-router";
import { fetchAgent } from "@/features/agents/services/agentsApi";
import { getAgentBySlug, rememberAgent } from "@/features/agents/services/agentsStorage";
import { DEFAULT_AGENT_ICON, EVA_AGENT_SLUG } from "@/features/agents/types/agent";
import { AGENT_SIZE } from "@/features/constructor/types/constructor";
import ConstructorView from "@/features/constructor/views/ConstructorView.vue";
import ProjectFormDialog from "@/features/projects/components/ProjectFormDialog.vue";
import ProjectsDesk from "@/features/projects/components/ProjectsDesk.vue";
import { useProjects } from "@/features/projects/composables/useProjects";
import type { Project } from "@/features/projects/types/project";
import { AGENT_ICON, type DeskAnchor } from "@/features/projects/utils/deskLayout";
import {
  createConstructorReadyGate,
  DESK_PASS_IDLE,
  flightIdentity,
  flightTo,
  handoffSeat,
  holdForLeave,
  holdFromRoute,
  passClearsHub,
  passDefersSatelliteReveal,
  passExitsToHub,
  useDeskMotion,
  type DeskPass,
  type Flight,
  type LeaveHold,
} from "@/features/projects/motion";
import {
  DESK_ASIDE_MS,
  DESK_EASE,
  DESK_EASE_OPEN,
  DESK_MOVE_MS,
} from "@/features/projects/utils/deskMotion";
import ProjectDeskView from "@/features/projects/views/ProjectDeskView.vue";
import {
  evaConstructorPath,
  isEvaConstructorSlug,
  projectPath,
  projectsPath,
} from "@/router/paths";
import AppMainNav from "@/shared/layout/AppMainNav.vue";

const props = defineProps<{
  projectSlug?: string;
  agentSlug?: string;
}>();

type HubStage = "eva" | "entering" | "project" | "eva-agent";

/** Eva sphere on the projects hub is `size-24`. */
const EVA_ICON = 96;
/** Runtime sphere on the project desk is also `size-24`. */
const RUNTIME_ICON = 96;

const router = useRouter();
const { projects, refresh, removeProject } = useProjects();
const createDialog = useTemplateRef("createDialog");
const hubDesk = useTemplateRef<{ rootEl: HTMLElement | null }>("hubDesk");
const projectDesk = useTemplateRef<{
  collapseDeskAgents: () => Promise<void>;
  revealDeskAgents: () => Promise<void>;
  prepareDeskAgents: () => Promise<void>;
}>("projectDesk");
const evaAnchor = useTemplateRef<HTMLButtonElement>("evaAnchor");
const deskAnchor = ref<DeskAnchor | null>(null);
const deskSize = ref({ width: 0, height: 0 });

const openedEva = isEvaConstructorSlug(props.projectSlug);
const openedProject = props.projectSlug && !openedEva ? props.projectSlug : null;

const stage = ref<HubStage>(openedEva ? "eva-agent" : openedProject ? "project" : "eva");
const focusSlug = ref<string | null>(openedProject);
const dimmed = ref(Boolean(openedEva));
const focusHidden = ref(false);
const evaHidden = ref(Boolean(openedEva));
const iconSnap = ref(false);
const evaSnap = ref(false);
const iconFlight = ref<Flight | null>(null);
const evaFlight = ref<Flight | null>(null);
const projectOn = ref(Boolean(openedProject));
const evaLayer = ref(!openedProject);
const evaConstructorOn = ref(Boolean(openedEva));
const hubVisible = ref(Boolean(openedEva));
const satellites = ref(Boolean(openedEva));
/** Project icons around Eva — collapse into her when opening the constructor. */
const hubSatellites = ref(!openedEva);
/** Cross-desk transition pass (replaces the old hubClear multi-flag). */
const deskPass = ref<DeskPass>(DESK_PASS_IDLE);
const hubClear = computed(() => passClearsHub(deskPass.value));
const showMeta = ref(Boolean(openedEva));
const bootPan = ref<{ x: number; y: number } | null>(null);
const glyphScale = ref(1);
const glide = ref(false);
const glideEase = ref(DESK_EASE);
const glideMs = ref(DESK_MOVE_MS);
const glideDelay = ref(0);
const glideTo = ref<{ x: number; y: number } | null>(null);
const worldAt = ref<{ x: number; y: number } | null>(null);
/**
 * Nested project desk mount: follow the route while open; freeze slugs on leave
 * because the router clears project/agent before the exit pass finishes.
 */
type ProjectHold = { projectSlug: string; agentSlug?: string };
const projectHold = ref<LeaveHold<ProjectHold> | null>(
  openedProject
    ? holdFromRoute({ projectSlug: openedProject, agentSlug: props.agentSlug })
    : null,
);
const mountedProjectSlug = computed(() => projectHold.value?.projectSlug ?? null);
const mountedAgentSlug = computed(() => projectHold.value?.agentSlug);
let settleOnReady = Boolean(openedEva);
const { beginPass, isCurrent, cancelPasses, wait, frame, reducedMotion } = useDeskMotion();
const { releaseReady, waitForConstructor } = createConstructorReadyGate();
let anchorObserver: ResizeObserver | null = null;

const edgeButtonClass =
  "btn border border-base-300/60 bg-base-100/90 shadow-lg backdrop-blur-sm transition-[opacity,transform] motion-reduce:transition-none";

const evaChromeClass = computed(() => {
  if (evaHidden.value) return "pointer-events-none opacity-0";
  // Stay solid and on top while flying into the constructor — dimming would hide the flight.
  if (evaFlight.value) return "z-50 opacity-100 pointer-events-none";
  if (dimmed.value) return "z-10 opacity-30 pointer-events-none";
  return "z-40 opacity-100";
});

const chromeStyle = { transitionDuration: `${DESK_ASIDE_MS}ms` };

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  if (document.querySelector("[data-channel-mode]")) return;
  const target = event.target;
  if (target instanceof HTMLElement && target.closest("input, textarea, select, [contenteditable='true']")) {
    return;
  }
  if (stage.value === "eva-agent") {
    event.preventDefault();
    void backToEvaHub();
  }
}

onMounted(() => {
  void refresh();
  void ensureEvaAgent();
  document.addEventListener("keydown", onKeydown);
  void nextTick(() => {
    measureDesk();
    anchorObserver = new ResizeObserver(measureDesk);
    const desk = hubDesk.value?.rootEl;
    if (desk) anchorObserver.observe(desk);
    anchorObserver.observe(document.documentElement);
  });
});

onUnmounted(() => {
  cancelPasses();
  releaseReady();
  document.removeEventListener("keydown", onKeydown);
  anchorObserver?.disconnect();
});

async function ensureEvaAgent() {
  if (getAgentBySlug(EVA_AGENT_SLUG)) return;
  try {
    rememberAgent(await fetchAgent(EVA_AGENT_SLUG));
  } catch {
    // Created on backend startup; ignore until API is up.
  }
}

function hubDeskEl(): HTMLElement | null {
  return hubDesk.value?.rootEl ?? null;
}

function measureDesk() {
  const button = evaAnchor.value;
  const desk = hubDeskEl();
  const icon = button?.querySelector("img");
  if (desk) {
    deskSize.value = { width: desk.clientWidth, height: desk.clientHeight };
  }
  if (!button || !desk || !icon) return;
  const iconRect = icon.getBoundingClientRect();
  const deskRect = desk.getBoundingClientRect();
  deskAnchor.value = {
    x: Math.round((iconRect.left + iconRect.width / 2 - deskRect.left) * 10) / 10,
    y: Math.round((iconRect.top + iconRect.height / 2 - deskRect.top) * 10) / 10,
  };
}

function measureFocus(): { x: number; y: number; width: number } | null {
  const slug = focusSlug.value;
  const desk = hubDeskEl();
  if (!slug || !desk) return null;
  const img = desk.querySelector(`[data-project="${CSS.escape(slug)}"] img`);
  if (!(img instanceof HTMLElement)) return null;
  const deskRect = desk.getBoundingClientRect();
  const rect = img.getBoundingClientRect();
  return {
    x: rect.left + rect.width / 2 - deskRect.left,
    y: rect.top + rect.height / 2 - deskRect.top,
    width: rect.width,
  };
}

function measureEvaIcon(): { x: number; y: number; width: number } | null {
  const button = evaAnchor.value;
  const desk = hubDeskEl();
  const icon = button?.querySelector("img");
  if (!button || !desk || !icon) return null;
  const deskRect = desk.getBoundingClientRect();
  const rect = icon.getBoundingClientRect();
  return {
    x: rect.left + rect.width / 2 - deskRect.left,
    y: rect.top + rect.height / 2 - deskRect.top,
    width: rect.width,
  };
}

function deskCenter(): { x: number; y: number } {
  return { x: deskSize.value.width / 2, y: deskSize.value.height / 2 };
}

function onConstructorReady() {
  if (settleOnReady) {
    settleOnReady = false;
    hubVisible.value = true;
    if (stage.value === "eva-agent") satellites.value = true;
  }
  releaseReady();
}

watch(projects, () => {
  void nextTick(measureDesk);
});

async function openProject(project: Project) {
  if (stage.value !== "eva") return;
  await router.push(projectPath(project.slug));
}

async function openEva() {
  if (stage.value !== "eva") return;
  await ensureEvaAgent();
  await router.push(evaConstructorPath());
}

async function backToEvaHub() {
  if (stage.value === "eva") return;
  await router.push(projectsPath());
}

async function onCreated(project: Project) {
  await router.push(projectPath(project.slug));
}

function remove(project: Project) {
  if (!confirm(`Удалить проект «${project.name}»? Агенты останутся в библиотеке.`)) return;
  void removeProject(project.slug);
}

const evaFlightStyle = computed(() => {
  const flight = evaFlight.value;
  if (!flight) {
    return {
      transform: "translateX(-50%) scale(1)",
      // Snap opacity with class changes — chromeStyle duration alone can still blink.
      transition: "none",
    };
  }
  return {
    transform: `translateX(-50%) translate(${flight.dx}px, ${flight.dy}px) scale(${flight.scale})`,
    transition:
      evaSnap.value || evaHidden.value
        ? "none"
        : `transform ${DESK_MOVE_MS}ms ${DESK_EASE_OPEN}`,
  };
});

async function enterEvaConstructor() {
  if (stage.value === "eva-agent") return;
  if (stage.value === "project") {
    await leaveProject();
  }
  const token = beginPass();
  settleOnReady = false;
  stage.value = "entering";
  projectHold.value = null;
  projectOn.value = false;
  deskPass.value = DESK_PASS_IDLE;
  evaLayer.value = true;
  evaHidden.value = false;
  focusHidden.value = false;
  satellites.value = false;
  hubVisible.value = false;
  evaConstructorOn.value = false;
  glide.value = false;
  glideTo.value = null;
  showMeta.value = false;
  iconFlight.value = null;
  // Keep Eva opaque/on-top from the first frame of the pass (avoids a dim flash).
  evaSnap.value = true;
  evaFlight.value = flightIdentity();
  dimmed.value = true;

  // One pass: projects collapse into Eva while she flies into the constructor.
  hubSatellites.value = false;

  if (reducedMotion()) {
    measureDesk();
    bootPan.value = deskCenter();
    glyphScale.value = 1;
    evaHidden.value = true;
    evaFlight.value = null;
    evaSnap.value = false;
    hubVisible.value = true;
    satellites.value = true;
    showMeta.value = true;
    evaConstructorOn.value = true;
    stage.value = "eva-agent";
    return;
  }

  measureDesk();
  const start = measureEvaIcon() ?? deskCenter();
  const center = deskCenter();
  bootPan.value = start;
  glyphScale.value = EVA_ICON / AGENT_SIZE;
  hubVisible.value = false;
  glideDelay.value = 0;
  glideMs.value = DESK_MOVE_MS;

  const flight = {
    dx: center.x - start.x,
    dy: center.y - start.y,
    scale: AGENT_SIZE / EVA_ICON,
  };
  await nextTick();
  await frame();
  await frame();
  if (!isCurrent(token)) return;
  evaSnap.value = false;
  evaFlight.value = flight;
  const flightStarted = performance.now();
  const ready = waitForConstructor();
  evaConstructorOn.value = true;
  await ready;
  if (!isCurrent(token)) return;
  // Handoff from Eva's *current* mid-flight pose — not the destination —
  // so a fast constructor ready doesn't skip the visible flight.
  const here = measureEvaIcon();
  const elapsed = Math.min(DESK_MOVE_MS, Math.max(0, performance.now() - flightStarted));
  const remain = Math.max(0, DESK_MOVE_MS - elapsed);
  if (here) {
    bootPan.value = { x: here.x, y: here.y };
    glyphScale.value = here.width > 0 ? here.width / AGENT_SIZE : 1;
  } else {
    const t = DESK_MOVE_MS > 0 ? elapsed / DESK_MOVE_MS : 1;
    bootPan.value = { x: start.x + flight.dx * t, y: start.y + flight.dy * t };
    glyphScale.value = (1 + (flight.scale - 1) * t) * (EVA_ICON / AGENT_SIZE);
  }
  await nextTick();
  await frame();
  if (!isCurrent(token)) return;
  // Land the constructor hub first, then drop Eva on the next frame (no opacity gap).
  if (
    !(await handoffSeat({
      land: () => {
        hubVisible.value = true;
        showMeta.value = true;
        satellites.value = true;
      },
      drop: () => {
        evaHidden.value = true;
        evaFlight.value = null;
      },
      token,
      isCurrent,
    }))
  ) {
    return;
  }
  if (remain < 48) {
    bootPan.value = center;
    glyphScale.value = 1;
    worldAt.value = center;
    stage.value = "eva-agent";
    return;
  }
  glideMs.value = remain;
  glideEase.value = DESK_EASE_OPEN;
  glide.value = true;
  await nextTick();
  await frame();
  if (!isCurrent(token)) return;
  glyphScale.value = 1;
  glideTo.value = center;
  await wait(remain);
  if (!isCurrent(token)) return;
  glide.value = false;
  glideDelay.value = 0;
  glideMs.value = DESK_MOVE_MS;
  worldAt.value = center;
  await nextTick();
  if (!isCurrent(token)) return;
  stage.value = "eva-agent";
}

async function leaveEvaConstructor() {
  if (stage.value === "eva" || stage.value === "project") return;
  const token = beginPass();
  settleOnReady = false;
  releaseReady();

  if (reducedMotion()) {
    evaConstructorOn.value = false;
    satellites.value = false;
    hubVisible.value = false;
    evaHidden.value = false;
    dimmed.value = false;
    evaFlight.value = null;
    glide.value = false;
    glideTo.value = null;
    glyphScale.value = 1;
    hubSatellites.value = true;
    stage.value = "eva";
    return;
  }

  showMeta.value = false;
  measureDesk();
  const home = deskAnchor.value ?? measureEvaIcon();
  if (!home) {
    evaConstructorOn.value = false;
    satellites.value = false;
    hubVisible.value = false;
    evaHidden.value = false;
    dimmed.value = false;
    hubSatellites.value = true;
    stage.value = "eva";
    return;
  }

  // One pass: constructor satellites collapse, hub glides home, projects expand from Eva.
  glideEase.value = DESK_EASE;
  glideDelay.value = 0;
  glideMs.value = DESK_MOVE_MS;
  glide.value = true;
  await nextTick();
  await frame();
  if (!isCurrent(token)) return;
  glyphScale.value = EVA_ICON / AGENT_SIZE;
  glideTo.value = { x: home.x, y: home.y };
  satellites.value = false;
  hubSatellites.value = true;
  dimmed.value = false;
  await wait(DESK_MOVE_MS);
  if (!isCurrent(token)) return;

  // Show Eva under the hub, then remove the constructor on the next frame.
  if (
    !(await handoffSeat({
      land: () => {
        evaSnap.value = true;
        evaFlight.value = flightIdentity();
        evaHidden.value = false;
      },
      drop: () => {
        hubVisible.value = false;
        evaConstructorOn.value = false;
        glide.value = false;
        glideTo.value = null;
        glyphScale.value = 1;
      },
      token,
      isCurrent,
    }))
  ) {
    return;
  }
  await nextTick();
  await frame();
  if (!isCurrent(token)) return;
  evaSnap.value = false;
  evaFlight.value = null;
  stage.value = "eva";
}

async function enterProject(slug: string) {
  if (stage.value === "eva-agent") {
    await leaveEvaConstructor();
  }
  projectHold.value = holdFromRoute({ projectSlug: slug, agentSlug: props.agentSlug });
  if (stage.value !== "eva") {
    focusSlug.value = slug;
    projectOn.value = true;
    evaLayer.value = false;
    deskPass.value = DESK_PASS_IDLE;
    stage.value = "project";
    return;
  }
  const token = beginPass();
  stage.value = "entering";
  focusSlug.value = slug;
  dimmed.value = true;
  focusHidden.value = false;
  iconSnap.value = false;
  iconFlight.value = null;
  evaLayer.value = true;

  if (reducedMotion()) {
    focusHidden.value = true;
    dimmed.value = false;
    evaLayer.value = false;
    deskPass.value = DESK_PASS_IDLE;
    projectOn.value = true;
    stage.value = "project";
    return;
  }

  measureDesk();
  await nextTick();
  await frame();
  const start = measureFocus();
  const target = deskAnchor.value;
  if (!start || !target) {
    focusHidden.value = true;
    dimmed.value = false;
    evaLayer.value = false;
    deskPass.value = DESK_PASS_IDLE;
    projectOn.value = true;
    stage.value = "project";
    return;
  }

  // Mount under a clear hub, arm collapsed agents, then start flight + burst together.
  deskPass.value = { kind: "evaToProject", phase: "fly" };
  projectOn.value = true;
  await nextTick();
  await frame();
  if (!isCurrent(token)) return;
  await projectDesk.value?.prepareDeskAgents();
  if (!isCurrent(token)) return;

  iconSnap.value = true;
  iconFlight.value = flightIdentity();
  await nextTick();
  await frame();
  await frame();
  if (!isCurrent(token)) return;
  iconSnap.value = false;
  iconFlight.value = flightTo(start, target, RUNTIME_ICON / AGENT_ICON);
  void projectDesk.value?.revealDeskAgents();
  await wait(DESK_MOVE_MS);
  if (!isCurrent(token)) return;

  // Seat the runtime under the flyer, then drop the flyer next frame.
  if (
    !(await handoffSeat({
      land: () => {
        dimmed.value = false;
        deskPass.value = DESK_PASS_IDLE;
      },
      drop: () => {
        focusHidden.value = true;
        iconFlight.value = null;
        evaLayer.value = false;
      },
      token,
      isCurrent,
    }))
  ) {
    return;
  }
  stage.value = "project";
}

async function leaveProject() {
  if (stage.value === "eva" || stage.value === "eva-agent") return;
  const slug =
    projectHold.value?.projectSlug || focusSlug.value || props.projectSlug || null;
  const token = beginPass();
  stage.value = "entering";

  if (reducedMotion() || !slug) {
    projectHold.value = null;
    projectOn.value = false;
    deskPass.value = DESK_PASS_IDLE;
    focusHidden.value = false;
    iconFlight.value = null;
    iconSnap.value = false;
    dimmed.value = false;
    focusSlug.value = null;
    evaLayer.value = true;
    stage.value = "eva";
    return;
  }

  // Freeze mount against the already-cleared route for the exit pass.
  projectHold.value = holdForLeave(projectHold.value, {
    projectSlug: slug,
    agentSlug: projectHold.value?.agentSlug,
  });

  // Bring the hub back so flight + collapses share one pass (desk shows through clear hub).
  evaLayer.value = true;
  focusSlug.value = slug;
  dimmed.value = true;
  focusHidden.value = true;
  await nextTick();
  measureDesk();
  await frame();
  if (!isCurrent(token)) return;

  const slot = measureFocus();
  const target = deskAnchor.value;
  if (!slot || !target) {
    projectHold.value = null;
    projectOn.value = false;
    deskPass.value = DESK_PASS_IDLE;
    focusHidden.value = false;
    iconFlight.value = null;
    dimmed.value = false;
    focusSlug.value = null;
    stage.value = "eva";
    return;
  }

  // Put the hub flyer on the runtime seat first, then hide the desk runtime.
  iconSnap.value = true;
  iconFlight.value = flightTo(slot, target, RUNTIME_ICON / AGENT_ICON);
  if (
    !(await handoffSeat({
      land: () => {
        focusHidden.value = false;
      },
      drop: () => {
        deskPass.value = { kind: "projectToEva", phase: "fly" };
      },
      token,
      isCurrent,
    }))
  ) {
    return;
  }

  // Agent leave (if any), desk-agent collapse, and reverse flight start together.
  if (projectHold.value) {
    projectHold.value = { ...projectHold.value, agentSlug: undefined };
  }
  void projectDesk.value?.collapseDeskAgents();
  await nextTick();
  await frame();
  await frame();
  if (!isCurrent(token)) return;
  iconSnap.value = false;
  iconFlight.value = flightIdentity();
  await wait(DESK_MOVE_MS);
  if (!isCurrent(token)) return;

  // Flyer is on the orbit slot — clear the desk, then release hub chrome.
  if (
    !(await handoffSeat({
      land: () => {
        projectOn.value = false;
        projectHold.value = null;
        iconSnap.value = true;
        iconFlight.value = null;
      },
      drop: () => {
        deskPass.value = DESK_PASS_IDLE;
        dimmed.value = false;
        focusSlug.value = null;
        focusHidden.value = false;
        iconSnap.value = false;
      },
      token,
      isCurrent,
    }))
  ) {
    return;
  }
  stage.value = "eva";
}

watch(
  () => props.projectSlug || null,
  (slug) => {
    if (isEvaConstructorSlug(slug)) void enterEvaConstructor();
    else if (slug) void enterProject(slug);
    else if (stage.value === "eva-agent") void leaveEvaConstructor();
    else void leaveProject();
  },
);

watch(
  () => props.agentSlug,
  (slug) => {
    const hold = projectHold.value;
    if (hold?.source === "route") {
      projectHold.value = holdFromRoute({
        projectSlug: hold.projectSlug,
        agentSlug: slug,
      });
    }
  },
);
</script>

<template>
  <div class="relative h-full min-h-0 w-full overflow-hidden">
    <div
      v-show="evaLayer"
      class="absolute inset-0"
      :class="hubClear || evaFlight ? 'z-40' : projectOn || evaConstructorOn ? 'z-10' : 'z-20'"
    >
      <ProjectsDesk
        ref="hubDesk"
        class="h-full"
        :projects="projects"
        :anchor="deskAnchor"
        :focus-slug="focusSlug"
        :dimmed="dimmed"
        :focus-hidden="focusHidden"
        :satellites="hubSatellites"
        :icon-flight="iconFlight"
        :icon-snap="iconSnap"
        :clear-backdrop="hubClear"
        @open="openProject"
        @remove="remove"
        @create="createDialog?.open()"
      />

      <div
        class="pointer-events-none absolute inset-x-0 top-0 z-40 flex justify-center px-4 pt-4 transition-opacity motion-reduce:transition-none"
        :class="hubClear || dimmed || evaConstructorOn ? 'opacity-0' : 'opacity-100'"
        :style="chromeStyle"
      >
        <div
          class="rounded-box border border-base-300/60 bg-base-100/90 px-2 shadow-lg backdrop-blur-sm"
          :class="dimmed || evaConstructorOn ? 'pointer-events-none' : 'pointer-events-auto'"
        >
          <AppMainNav />
        </div>
      </div>

      <button
        type="button"
        ref="evaAnchor"
        data-agent="eva"
        :class="[
          hubClear ? 'pointer-events-none opacity-0' : evaChromeClass,
          'absolute bottom-6 left-1/2 flex w-max max-w-48 flex-col items-center gap-1.5 text-center outline-none focus:outline-none focus-visible:outline-none motion-reduce:transition-none',
        ]"
        :style="{ ...chromeStyle, ...evaFlightStyle }"
        aria-label="Ева, системный агент ведения проектов"
        @click="openEva"
      >
        <img
          :src="DEFAULT_AGENT_ICON"
          alt=""
          class="size-24 rounded-full border border-base-300 bg-base-100 object-cover shadow-lg"
        />
        <span
          class="text-sm font-medium leading-tight transition-opacity motion-reduce:transition-none"
          :class="dimmed || evaFlight ? 'opacity-0' : 'opacity-100'"
          :style="chromeStyle"
        >Ева</span>
        <span
          class="text-xs leading-tight text-base-content/50 transition-opacity motion-reduce:transition-none"
          :class="dimmed || evaFlight ? 'opacity-0' : 'opacity-100'"
          :style="chromeStyle"
        >проекты</span>
      </button>

    </div>

    <div v-if="evaConstructorOn" class="absolute inset-0 z-30">
      <ConstructorView
        class="h-full"
        :agent-slug="EVA_AGENT_SLUG"
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
        @click="backToEvaHub"
      >
        К проектам
      </button>
    </div>

    <div v-if="projectOn && mountedProjectSlug" class="absolute inset-0 z-30">
      <ProjectDeskView
        ref="projectDesk"
        :project-slug="mountedProjectSlug"
        :agent-slug="mountedAgentSlug"
        :defer-satellite-reveal="passDefersSatelliteReveal(deskPass)"
        :exiting-to-hub="passExitsToHub(deskPass)"
      />
    </div>

    <ProjectFormDialog ref="createDialog" mode="create" @saved="onCreated" />
  </div>
</template>
