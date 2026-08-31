<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from "vue";
import { useRouter } from "vue-router";
import type { AgentSaveStatus } from "@/features/agents/services/agentsStorage";
import { agentSaveStatus, flushAgentsToApi } from "@/features/agents/services/agentsStorage";
import { useSkills } from "@/features/skills/composables/useSkills";
import { skillPath } from "@/router/paths";

const props = defineProps<{
  agentSlug: string;
  skillId: string;
  errorCount?: number;
  warningCount?: number;
}>();

const emit = defineEmits<{
  home: [];
  exportYaml: [];
  importYaml: [];
  showValidation: [];
}>();

const router = useRouter();
const { getSkills } = useSkills();

const helpOpen = ref(false);
const rootEl = useTemplateRef<HTMLElement>("root");
const saving = ref(false);

const skills = computed(() => getSkills(props.agentSlug));

const currentSkill = computed(
  () => skills.value.find((skill) => skill.id === props.skillId) ?? null,
);

const saveLabel = computed(() => {
  const labels: Record<AgentSaveStatus, string> = {
    idle: "Черновик",
    saving: "Сохранение…",
    saved: "В БД",
    error: "Ошибка",
    offline: "Локально",
  };
  return labels[agentSaveStatus.value];
});

const saveClass = computed(() => {
  switch (agentSaveStatus.value) {
    case "saved":
      return "badge-success";
    case "saving":
      return "badge-ghost";
    case "error":
      return "badge-error";
    case "offline":
      return "badge-warning";
    default:
      return "badge-ghost";
  }
});

async function saveNow() {
  saving.value = true;
  try {
    await flushAgentsToApi();
  } catch {
    // status badge shows error
  } finally {
    saving.value = false;
  }
}

const shortcuts = [
  { keys: "Колёсико", action: "Масштаб холста" },
  { keys: "Перетаскивание фона", action: "Панорама" },
  { keys: "State", action: "Нарисовать состояние FSM" },
  { keys: "Transition", action: "Клик на стороне источника → клик на стороне цели" },
  { keys: "Выбранная стрелка", action: "Тяните кружки на концах, чтобы переподключить" },
  { keys: "Выбранный state", action: "Тяните углы и стороны, чтобы изменить размер" },
  { keys: "Delete / Backspace", action: "Удалить state или transition" },
];

function onDocumentPointerDown(event: PointerEvent) {
  if (!helpOpen.value) return;
  const target = event.target;
  if (target instanceof Node && rootEl.value?.contains(target)) return;
  helpOpen.value = false;
}

async function onSkillChange(event: Event) {
  const nextId = (event.target as HTMLSelectElement).value;
  if (!nextId || nextId === props.skillId) return;
  await router.push(skillPath(props.agentSlug, nextId));
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
});
</script>

<template>
  <div
    ref="root"
    class="absolute left-4 top-4 z-20 flex items-center gap-1 rounded-box border border-base-300/60 bg-base-100/90 px-2 py-2 shadow-lg backdrop-blur-sm"
  >
    <button
      type="button"
      class="btn btn-xs btn-square btn-ghost"
      title="К списку Skills"
      aria-label="К списку Skills"
      @click="emit('home')"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 18 9 12l6-6" />
      </svg>
    </button>

    <select
      v-if="skills.length"
      class="select select-xs h-7 min-h-0 max-w-44 border-base-300/60 bg-base-100/80 py-0 pl-2 pr-7 text-xs font-medium"
      :value="skillId"
      :title="currentSkill?.name ?? 'Skill'"
      aria-label="Переключить Skill"
      @change="onSkillChange"
    >
      <option v-for="item in skills" :key="item.id" :value="item.id">
        {{ item.name }}
      </option>
    </select>
    <span v-else class="max-w-40 truncate text-xs text-base-content/60">
      {{ currentSkill?.name ?? "Skill" }}
    </span>

    <button
      type="button"
      class="btn btn-xs btn-ghost gap-1"
      :disabled="saving || agentSaveStatus === 'offline'"
      title="Сохранить черновик агента в PostgreSQL"
      @click="saveNow"
    >
      <span class="badge badge-xs" :class="saveClass">{{ saveLabel }}</span>
    </button>

    <button
      v-if="(errorCount ?? 0) > 0 || (warningCount ?? 0) > 0"
      type="button"
      class="btn btn-xs btn-ghost gap-1 font-mono"
      title="Показать validation issues"
      @click="emit('showValidation')"
    >
      <span v-if="(errorCount ?? 0) > 0" class="badge badge-xs badge-error">{{ errorCount }} err</span>
      <span v-if="(warningCount ?? 0) > 0" class="badge badge-xs badge-warning">{{ warningCount }} warn</span>
    </button>

    <button
      type="button"
      class="btn btn-xs btn-ghost"
      title="Export YAML"
      @click="emit('exportYaml')"
    >
      YAML↓
    </button>
    <button
      type="button"
      class="btn btn-xs btn-ghost"
      title="Import YAML"
      @click="emit('importYaml')"
    >
      YAML↑
    </button>

    <div class="relative">
      <button
        type="button"
        class="btn btn-xs btn-circle btn-ghost"
        title="Справка"
        aria-label="Справка"
        :aria-expanded="helpOpen"
        @click="helpOpen = !helpOpen"
      >
        ?
      </button>

      <div
        v-if="helpOpen"
        class="absolute left-0 top-full mt-2 w-72 rounded-box border border-base-300 bg-base-100 p-4 shadow-xl"
      >
        <p class="mb-3 text-sm font-medium">Управление</p>
        <ul class="space-y-2">
          <li
            v-for="item in shortcuts"
            :key="item.keys"
            class="flex flex-col gap-0.5 text-sm"
          >
            <span class="font-medium">{{ item.keys }}</span>
            <span class="text-base-content/60">{{ item.action }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
