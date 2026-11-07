<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch } from "vue";
import { agentIconSrc, type Agent } from "@/features/agents/types/agent";
import type { AgentHubStatus, AgentHubTone } from "@/features/constructor/utils/agentHubStatus";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { agentOverviewPath, agentRuntimePath } from "@/router/paths";
import { DESK_ASIDE_MS, DESK_EASE, DESK_MOVE_MS } from "@/features/projects/utils/deskMotion";
import { formatDateTime } from "@/shared/utils/formatDate";

export type AgentHubPhase = "circle" | "card" | "details";

const TONE_DOT: Record<AgentHubTone, string> = {
  neutral: "bg-base-content/30",
  success: "bg-success",
  warning: "bg-warning",
};

const CARD_RUN_STATUSES = new Set(["running", "waiting", "error"]);

const props = defineProps<{
  phase: AgentHubPhase;
  /** `null` while loading or when runtime is unreachable. */
  status: AgentHubStatus | null;
  statusLoading?: boolean;
  statusError?: string | null;
  agent: Pick<
    Agent,
    | "name"
    | "description"
    | "icon"
    | "slug"
    | "createdAt"
    | "updatedAt"
    | "skills"
    | "actions"
    | "tools"
    | "constructorLayout"
  >;
  panX: number;
  panY: number;
  zoom: number;
  /** False while the project desk is still carrying the icon to the center. */
  visible?: boolean;
  /** 1 matches the hub. Smaller while the icon is still the desk size. */
  glyphScale?: number;
  /** Animate left, top, and scale. Turn on only after the start pose has painted. */
  glide?: boolean;
  glideEase?: string;
  glideMs?: number;
  /** Negative values join a flight that already started, in milliseconds. */
  glideDelay?: number;
  /** Name and status under the circle. Hidden while the icon is still leaving the desk. */
  showMeta?: boolean;
  /** Step aside while a channel occupies the center. */
  parked?: boolean;
}>();

const emit = defineEmits<{
  open: [];
  closeCard: [];
  openDetails: [];
  closeDetails: [];
  update: [patch: { name?: string; description?: string; icon?: string }];
}>();

const MORPH_MS = 420;
const EASING = "cubic-bezier(0.22, 1, 0.36, 1)";

const editing = ref(false);
const draftName = ref(props.agent.name);
const draftDescription = ref(props.agent.description);
const iconInput = ref<HTMLInputElement | null>(null);
const nameInput = ref<HTMLInputElement | null>(null);
const shellEl = useTemplateRef<HTMLElement>("shell");
/** Holds fullscreen layout during expand FLIP before phase paints as details. */
const flipHold = ref<"none" | "expand" | "collapse">("none");
const contentReady = ref(props.phase !== "circle");

watch(
  () => [props.agent.name, props.agent.description] as const,
  ([name, description]) => {
    if (editing.value) return;
    draftName.value = name;
    draftDescription.value = description;
  },
);

watch(
  () => props.phase,
  (phase) => {
    if (phase === "circle") {
      editing.value = false;
      contentReady.value = false;
      return;
    }
    if (phase === "card") {
      window.setTimeout(() => {
        if (props.phase === "card") contentReady.value = true;
      }, MORPH_MS * 0.4);
      return;
    }
    contentReady.value = true;
  },
);

watch(
  () => props.phase,
  async (phase, prev) => {
    if (!prev || prev === phase) return;
    if (prev !== "details" && phase === "details") {
      await runFlip("expand");
      shellEl.value?.focus();
      return;
    }
    if (prev === "details" && phase !== "details") {
      await runFlip("collapse");
    }
  },
  { flush: "pre" },
);

const iconSrc = computed(() => agentIconSrc(props.agent));
const canResetIcon = computed(() => Boolean(props.agent.icon.trim()));
const enabledTools = computed(() => props.agent.tools.filter((tool) => tool.enabled));
const channelCount = computed(
  () => enabledTools.value.filter((tool) => getToolDefinition(tool.toolId)?.world).length,
);
const configurationCounts = computed(() => [
  { label: "Навыки", count: props.agent.skills.length },
  { label: "Actions", count: props.agent.actions.length },
  { label: "Каналы", count: channelCount.value },
  { label: "Плагины", count: enabledTools.value.length - channelCount.value },
]);
const hasRunningRuns = computed(
  () => props.status?.runs.some((run) => run.status === "running" && run.count > 0) ?? false,
);
const cardRunLine = computed(
  () =>
    props.status?.runs
      .filter((run) => CARD_RUN_STATUSES.has(run.status))
      .map((run) => `${run.label} ${run.count}`)
      .join(" · ") ?? "",
);
const overviewHref = computed(() => agentOverviewPath(props.agent.slug));
const runtimeHref = computed(() => agentRuntimePath(props.agent.slug));

const showFullscreenLayout = computed(
  () => props.phase === "details" || flipHold.value === "expand",
);

const shellMode = computed<"circle" | "card" | "details">(() => {
  if (flipHold.value === "expand" || props.phase === "details") return "details";
  if (flipHold.value === "collapse") return props.phase === "circle" ? "circle" : "card";
  return props.phase;
});

const rootStyle = computed(() => {
  if (showFullscreenLayout.value) {
    return {
      left: "0px",
      top: "0px",
      width: "100%",
      height: "100%",
      transform: "none",
      zIndex: "40",
    };
  }
    const ms = props.glideMs ?? DESK_MOVE_MS;
    const ease = props.glideEase || DESK_EASE;
    const delay = props.glideDelay ?? 0;
    return {
      left: `${props.panX}px`,
      top: `${props.panY}px`,
      width: "auto",
      height: "auto",
      transform: `translate(-50%, -50%) scale(${props.zoom * (props.glyphScale ?? 1)})`,
      transition:
        props.glide && !showFullscreenLayout.value
          ? `left ${ms}ms ${ease} ${delay}ms, top ${ms}ms ${ease} ${delay}ms, transform ${ms}ms ${ease} ${delay}ms`
          : "none",
      zIndex: "20",
    };
});

async function runFlip(direction: "expand" | "collapse") {
  const shell = shellEl.value;
  if (!shell) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const first = shell.getBoundingClientRect();
  flipHold.value = direction;
  await nextTick();
  const last = shell.getBoundingClientRect();

  if (last.width < 2 || last.height < 2 || first.width < 2 || first.height < 2) {
    flipHold.value = "none";
    return;
  }

  const dx = first.left - last.left;
  const dy = first.top - last.top;
  const sx = first.width / last.width;
  const sy = first.height / last.height;

  shell.style.transformOrigin = "top left";
  shell.style.transition = "none";
  shell.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`;
  shell.style.borderRadius = direction === "expand" ? "1.5rem" : "0px";

  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        shell.style.transition = `transform ${MORPH_MS}ms ${EASING}, border-radius ${MORPH_MS}ms ${EASING}`;
        shell.style.transform = "none";
        shell.style.borderRadius = direction === "expand" ? "0px" : "1.5rem";
        window.setTimeout(() => {
          shell.style.transition = "";
          shell.style.transform = "";
          shell.style.transformOrigin = "";
          shell.style.borderRadius = "";
          flipHold.value = "none";
          resolve();
        }, MORPH_MS);
      });
    });
  });
}

async function startEditing() {
  draftName.value = props.agent.name;
  draftDescription.value = props.agent.description;
  editing.value = true;
  await nextTick();
  nameInput.value?.focus();
  nameInput.value?.select();
}

function commitEdits() {
  const nextName = draftName.value.trim();
  const nextDescription = draftDescription.value.trim();
  const patch: { name?: string; description?: string } = {};
  if (nextName && nextName !== props.agent.name) patch.name = nextName;
  else draftName.value = props.agent.name;
  if (nextDescription !== props.agent.description) patch.description = nextDescription;
  if (Object.keys(patch).length) emit("update", patch);
  editing.value = false;
}

function cancelEditing() {
  draftName.value = props.agent.name;
  draftDescription.value = props.agent.description;
  editing.value = false;
}

async function readIconAsDataUrl(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file);
  const maxSide = 256;
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const width = Math.max(1, Math.round(bitmap.width * scale));
  const height = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    return "";
  }
  ctx.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  return canvas.toDataURL("image/jpeg", 0.85);
}

async function onIconFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || !file.type.startsWith("image/")) return;
  try {
    const result = await readIconAsDataUrl(file);
    if (result) emit("update", { icon: result });
  } catch {
    // ignore
  }
}

function resetIcon() {
  if (!canResetIcon.value) return;
  emit("update", { icon: "" });
}

function onShellClick() {
  if (props.phase === "circle") emit("open");
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  if (editing.value) {
    cancelEditing();
    return;
  }
  if (props.phase === "details") emit("closeDetails");
  else if (props.phase === "card") emit("closeCard");
}
</script>

<template>
  <div
    class="agent-hub-root pointer-events-none absolute"
    :class="visible === false ? 'opacity-0' : 'opacity-100'"
    :style="rootStyle"
    data-canvas-ui
  >
    <div
      :class="parked ? 'pointer-events-none opacity-0' : 'opacity-100'"
      :style="{ transition: 'none' }"
      :aria-hidden="parked ? 'true' : undefined"
    >
    <div
      ref="shell"
      class="agent-hub-shell relative flex flex-col overflow-hidden bg-base-100 outline-none"
      :class="{
        'pointer-events-none': visible === false || parked,
        'pointer-events-auto': visible !== false && !parked,
        'is-flipping': flipHold !== 'none',
        'is-settling': (glyphScale ?? 1) < 0.999,
        'agent-hub-shell--circle cursor-pointer border border-base-300 shadow-md hover:border-primary/50 hover:ring-2 hover:ring-primary/20':
          shellMode === 'circle',
        'agent-hub-shell--card border-2 border-base-300/70 shadow-xl': shellMode === 'card',
        'agent-hub-shell--details border-2 border-transparent shadow-2xl': shellMode === 'details',
      }"
      role="dialog"
      :aria-label="
        shellMode === 'circle' ? 'Агент' : shellMode === 'card' ? 'Карточка агента' : 'Детали агента'
      "
      :aria-expanded="shellMode !== 'circle'"
      :tabindex="shellMode === 'details' ? 0 : -1"
      @click="onShellClick"
      @keydown="onKeydown"
      @pointerdown.stop
    >
      <div
        class="agent-hub-layer absolute inset-0 flex items-center justify-center"
        :class="shellMode === 'circle' ? 'opacity-100' : 'pointer-events-none opacity-0'"
      >
        <img
          :src="iconSrc"
          alt=""
          class="absolute inset-0 size-full rounded-full object-cover"
        />
      </div>

      <div
        class="agent-hub-layer flex flex-col"
        :class="[
          shellMode === 'details' ? 'min-h-0 flex-1' : '',
          shellMode === 'circle'
            ? 'pointer-events-none opacity-0'
            : contentReady
              ? 'opacity-100'
              : 'opacity-0',
        ]"
        @click.stop
      >
        <header
          class="flex shrink-0 items-center justify-between gap-2"
          :class="shellMode === 'details' ? 'border-b border-base-300 px-5 py-3' : 'px-1 pb-1'"
        >
          <p
            class="text-xs font-semibold uppercase tracking-wide text-base-content/50 transition-opacity"
            :class="shellMode === 'details' ? 'opacity-100' : 'opacity-0'"
          >
            Агент
          </p>
          <div class="flex items-center gap-1">
            <button
              v-if="!editing"
              type="button"
              class="btn btn-ghost btn-square"
              :class="shellMode === 'details' ? 'btn-sm' : 'btn-xs'"
              title="Редактировать"
              aria-label="Редактировать"
              @click="startEditing"
            >
              <svg viewBox="0 0 24 24" class="size-3.5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 20h9" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
              </svg>
            </button>
            <template v-else>
              <button
                type="button"
                class="btn btn-ghost"
                :class="shellMode === 'details' ? 'btn-sm' : 'btn-xs btn-square'"
                @click="cancelEditing"
              >
                <template v-if="shellMode === 'details'">Отмена</template>
                <span v-else class="text-sm leading-none" aria-hidden="true">×</span>
              </button>
              <button
                type="button"
                class="btn"
                :class="
                  shellMode === 'details'
                    ? 'btn-sm btn-primary'
                    : 'btn-xs btn-square btn-ghost text-success'
                "
                @click="commitEdits"
              >
                <template v-if="shellMode === 'details'">Сохранить</template>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  class="size-3.5"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                  aria-hidden="true"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </button>
            </template>
            <button
              v-if="shellMode === 'details'"
              type="button"
              class="btn btn-ghost btn-sm btn-square"
              aria-label="Закрыть"
              @click="emit('closeDetails')"
            >
              <span class="text-lg leading-none" aria-hidden="true">×</span>
            </button>
          </div>
        </header>

        <div
          :class="
            shellMode === 'details'
              ? 'min-h-0 flex-1 overflow-y-auto px-5 py-8'
              : 'overflow-visible px-3 pb-3'
          "
        >
          <div
            class="mx-auto flex flex-col items-center gap-3 text-center"
            :class="shellMode === 'details' ? 'max-w-2xl gap-5' : ''"
          >
            <div class="relative">
              <button
                type="button"
                class="flex items-center justify-center overflow-hidden rounded-full border-2 border-base-300 bg-base-200 transition-[width,height] duration-300"
                :class="[
                  shellMode === 'details' ? 'size-28' : 'size-20',
                  editing ? 'cursor-pointer hover:border-primary/50' : 'cursor-default',
                ]"
                :disabled="!editing"
                :aria-label="editing ? 'Сменить иконку' : undefined"
                @click="editing && iconInput?.click()"
              >
                <img :src="iconSrc" alt="" class="size-full object-cover" />
              </button>
              <button
                v-if="editing && canResetIcon"
                type="button"
                class="btn btn-circle absolute -right-1 -top-1 border border-base-300 bg-base-100"
                :class="shellMode === 'details' ? 'btn-sm' : 'btn-xs'"
                title="Сбросить иконку"
                aria-label="Сбросить иконку"
                @click="resetIcon"
              >
                <span class="leading-none" aria-hidden="true">×</span>
              </button>
              <input
                ref="iconInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="onIconFile"
              />
            </div>

            <template v-if="editing">
              <input
                ref="nameInput"
                v-model="draftName"
                type="text"
                class="input input-bordered w-full text-center font-semibold"
                :class="shellMode === 'details' ? 'max-w-md text-2xl' : 'input-sm text-sm'"
                aria-label="Имя агента"
                @keydown.enter.prevent="commitEdits"
                @keydown.escape.prevent="cancelEditing"
              />
              <textarea
                v-model="draftDescription"
                class="textarea textarea-bordered w-full resize-y"
                :class="
                  shellMode === 'details' ? 'max-w-md min-h-28 text-sm' : 'textarea-sm min-h-20 text-sm'
                "
                placeholder="Описание агента"
                aria-label="Описание агента"
                @keydown.escape.prevent="cancelEditing"
              />
            </template>
            <template v-else>
              <h2
                class="w-full font-semibold tracking-tight"
                :class="shellMode === 'details' ? 'text-3xl' : 'line-clamp-2 text-sm'"
              >
                {{ agent.name }}
              </h2>
              <p v-if="shellMode === 'details'" class="font-mono text-sm text-base-content/50">
                /{{ agent.slug }}
              </p>
              <p
                v-if="agent.description"
                class="w-full text-base-content/70"
                :class="
                  shellMode === 'details'
                    ? 'max-w-xl text-base leading-relaxed'
                    : 'line-clamp-4 text-sm'
                "
              >
                {{ agent.description }}
              </p>
              <p v-else class="w-full text-sm italic text-base-content/40">
                {{ shellMode === 'details' ? 'Описание не задано' : 'Без описания' }}
              </p>
            </template>

            <div v-if="shellMode === 'details'" class="mt-2 grid w-full gap-4 text-left md:grid-cols-2">
              <section class="rounded-2xl border border-base-300 p-4" aria-labelledby="agent-hub-configuration">
                <h3 id="agent-hub-configuration" class="font-semibold">Конфигурация</h3>
                <p class="text-xs text-base-content/50">Что задано</p>
                <dl class="mt-3 grid grid-cols-2 gap-2">
                  <div
                    v-for="item in configurationCounts"
                    :key="item.label"
                    class="rounded-xl bg-base-200/50 px-3 py-2"
                  >
                    <dt class="text-xs text-base-content/50">{{ item.label }}</dt>
                    <dd class="text-lg font-semibold">{{ item.count }}</dd>
                  </div>
                </dl>
                <p class="mt-3 text-xs text-base-content/45">
                  Создан {{ formatDateTime(agent.createdAt) }} · обновлён
                  {{ formatDateTime(agent.updatedAt) }}
                </p>
              </section>

              <section class="rounded-2xl border border-base-300 p-4" aria-labelledby="agent-hub-execution">
                <h3 id="agent-hub-execution" class="font-semibold">Исполнение</h3>
                <p class="text-xs text-base-content/50">Что происходит</p>
                <template v-if="status">
                  <p class="mt-3 flex items-center gap-2 text-sm font-medium">
                    <span class="size-2 shrink-0 rounded-full" :class="TONE_DOT[status.tone]" aria-hidden="true" />
                    {{ status.headline }}
                  </p>
                  <p v-if="status.publishedAt" class="mt-0.5 text-xs text-base-content/50">
                    Опубликован {{ formatDateTime(status.publishedAt) }}
                  </p>
                  <p v-if="status.unpublishedParts.length" class="mt-1 text-xs text-warning">
                    Изменено после публикации: {{ status.unpublishedParts.join(", ") }}
                  </p>
                  <p v-if="!status.published" class="mt-1 text-xs text-base-content/60">
                    Runtime исполняет только опубликованную версию.
                  </p>
                  <dl class="mt-3 grid grid-cols-3 gap-2">
                    <div v-for="run in status.runs" :key="run.status" class="rounded-xl bg-base-200/50 px-3 py-2">
                      <dt class="text-xs text-base-content/50">{{ run.label }}</dt>
                      <dd
                        class="text-lg font-semibold"
                        :class="run.status === 'error' && run.count ? 'text-error' : ''"
                      >
                        {{ run.count }}
                      </dd>
                    </div>
                  </dl>
                </template>
                <p v-else class="mt-3 text-sm text-base-content/60">
                  {{
                    statusError
                      ? `Нет связи с runtime: ${statusError}`
                      : statusLoading
                        ? "Загрузка…"
                        : "Runtime не отвечает"
                  }}
                </p>
                <div class="mt-4 flex flex-wrap gap-2">
                  <RouterLink :to="overviewHref" class="btn btn-sm">Готовность и публикация</RouterLink>
                  <RouterLink :to="runtimeHref" class="btn btn-sm">Прогоны</RouterLink>
                </div>
              </section>
            </div>

            <div v-if="shellMode === 'card' && !editing" class="mt-1 flex w-full flex-col gap-2 text-left">
              <div v-if="status" class="rounded-xl border border-base-300 bg-base-200/40 px-3 py-2">
                <p class="flex items-center gap-2 text-xs font-medium">
                  <span class="size-2 shrink-0 rounded-full" :class="TONE_DOT[status.tone]" aria-hidden="true" />
                  {{ status.headline }}
                </p>
                <p v-if="status.unpublishedParts.length" class="mt-0.5 text-xs text-warning">
                  Изменено: {{ status.unpublishedParts.join(", ") }}
                </p>
                <p class="mt-1 text-xs text-base-content/60">{{ cardRunLine }}</p>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <RouterLink :to="overviewHref" class="btn btn-xs">Готовность</RouterLink>
                <RouterLink :to="runtimeHref" class="btn btn-xs">Прогоны</RouterLink>
              </div>
              <button type="button" class="btn btn-sm btn-primary w-full" @click="emit('openDetails')">
                Подробнее
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <span
      v-if="status"
      class="pointer-events-none absolute bottom-1.5 right-1.5 flex size-3.5 transition-opacity duration-200"
      :class="shellMode === 'circle' && showMeta !== false ? 'opacity-100' : 'opacity-0'"
      :title="status.headline"
      aria-hidden="true"
    >
      <span
        v-if="hasRunningRuns"
        class="absolute inset-0 animate-ping rounded-full opacity-60"
        :class="TONE_DOT[status.tone]"
      />
      <span class="relative size-3.5 rounded-full ring-2 ring-base-100" :class="TONE_DOT[status.tone]" />
    </span>

    <div
      class="pointer-events-none absolute left-1/2 top-[calc(100%+0.5rem)] max-w-[200px] -translate-x-1/2 rounded-box border border-base-300/50 bg-base-100/90 px-2.5 py-1 text-center shadow-sm backdrop-blur-sm transition-opacity duration-200"
      :class="shellMode === 'circle' && showMeta !== false ? 'opacity-100' : 'opacity-0'"
    >
      <p class="truncate text-xs font-semibold">{{ agent.name }}</p>
      <p v-if="status" class="truncate text-[10px] text-base-content/60">{{ status.compactLine }}</p>
    </div>
    </div>
  </div>
</template>

<style scoped>
.agent-hub-root {
  transform-origin: center center;
}

.agent-hub-shell {
  transform-origin: center center;
  transition:
    width 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    height 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    border-radius 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}

.agent-hub-shell--circle {
  width: 88px;
  height: 88px;
  border-radius: 9999px;
}

.agent-hub-shell--card {
  width: 18rem;
  height: auto;
  border-radius: 1.5rem;
}

.agent-hub-shell--details {
  width: 100%;
  height: 100%;
  border-radius: 0;
}

.agent-hub-shell.is-flipping,
.agent-hub-shell.is-settling {
  /* Size is already the circle; don't grow width on top of the glide. */
  transition: none;
}

.agent-hub-layer {
  transition: opacity 0.22s ease;
}

@media (prefers-reduced-motion: reduce) {
  .agent-hub-shell,
  .agent-hub-layer {
    transition: none !important;
  }
}
</style>
