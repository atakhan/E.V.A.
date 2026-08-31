<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAgents } from "@/features/agents/composables/useAgents";
import { actionUsageCount } from "@/features/agents/utils/validateAgent";
import { useActions } from "@/features/actions/composables/useActions";
import { normalizeActionId } from "@/features/actions/types/normalize";
import { getActionRecipeStatus } from "@/features/actions/utils/actionSidebarMeta";
import ActionEditor from "@/features/actions/components/ActionEditor.vue";
import { agentActionPath } from "@/router/paths";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  agentSlug: string;
}>();

const route = useRoute();
const router = useRouter();
const { getAgentBySlug } = useAgents();
const { getActions, createAction, isActionIdAvailable } = useActions();

const selectedId = ref<string | null>(null);
const searchQuery = ref("");
const createOpen = ref(false);
const formName = ref("");
const formId = ref("");
const formDescription = ref("");
const formError = ref<string | null>(null);
const idTouched = ref(false);

const agent = computed(() => getAgentBySlug(props.agentSlug));
const actions = computed(() => getActions(props.agentSlug));

const filteredActions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return actions.value;
  return actions.value.filter(
    (action) =>
      action.name.toLowerCase().includes(q) || action.id.toLowerCase().includes(q),
  );
});

const selected = computed(
  () => actions.value.find((action) => action.id === selectedId.value) ?? null,
);

function actionBadges(action: (typeof actions.value)[number]) {
  const badges: Array<{ label: string; class: string }> = [];
  if (!agent.value) return badges;
  const status = getActionRecipeStatus(agent.value, action);
  if (status === "empty") badges.push({ label: "0 steps", class: "badge-warning badge-xs" });
  else if (action.recipe.length) {
    badges.push({ label: `${action.recipe.length} steps`, class: "badge-ghost badge-xs" });
  }
  if (status === "tool_off") badges.push({ label: "tool off", class: "badge-warning badge-xs" });
  if (status === "unknown") badges.push({ label: "?", class: "badge-warning badge-xs" });
  if (agent.value && actionUsageCount(agent.value, action.id) === 0) {
    badges.push({ label: "unused", class: "badge-ghost badge-xs opacity-60" });
  }
  return badges;
}

watch(
  actions,
  (list) => {
    if (selectedId.value && !list.some((action) => action.id === selectedId.value)) {
      selectedId.value = list[0]?.id ?? null;
    }
    if (!selectedId.value && list[0]) {
      selectedId.value = list[0].id;
    }
  },
  { immediate: true },
);

function applyRouteQuery() {
  const action = route.query.action;
  if (typeof action === "string" && action && actions.value.some((item) => item.id === action)) {
    selectedId.value = action;
  }
  const create = route.query.create;
  if (typeof create === "string" && create) {
    formName.value = create.replace(/_/g, " ");
    formId.value = suggestId(create);
    formDescription.value = "";
    formError.value = null;
    idTouched.value = true;
    createOpen.value = true;
  }
}

watch(
  () => [route.query.action, route.query.create, actions.value.length] as const,
  () => applyRouteQuery(),
  { immediate: true },
);

watch(selectedId, (id) => {
  if (!id) return;
  const current = route.query.action;
  if (current === id) return;
  void router.replace(agentActionPath(props.agentSlug, id));
});

function selectAction(id: string) {
  selectedId.value = id;
}

function onActionIdChanged(newId: string) {
  selectedId.value = newId;
}

function openCreate() {
  formName.value = "";
  formId.value = suggestId("parse_request");
  formDescription.value = "";
  formError.value = null;
  idTouched.value = false;
  createOpen.value = true;
}

function suggestId(base: string): string {
  let candidate = normalizeActionId(base) || "action";
  let n = 2;
  while (!isActionIdAvailable(props.agentSlug, candidate)) {
    candidate = `${normalizeActionId(base) || "action"}_${n}`;
    n += 1;
  }
  return candidate;
}

watch(formName, (name) => {
  if (!createOpen.value || idTouched.value) return;
  formId.value = suggestId(name || "action");
});

function saveCreate() {
  formError.value = null;
  const result = createAction(props.agentSlug, {
    id: formId.value,
    name: formName.value,
    description: formDescription.value,
  });
  if (!result.ok) {
    formError.value = result.error;
    return;
  }
  selectedId.value = result.action.id;
  createOpen.value = false;
}
</script>

<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Actions</h2>
        <p class="text-sm text-base-content/60">
          Поступки агента: FSM вызывает Action, recipe исполняет Tools
        </p>
      </div>
      <button type="button" class="btn btn-sm" @click="openCreate">
        Новый Action
      </button>
    </div>

    <div
      v-if="actions.length === 0"
      class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-12 text-center"
    >
      <p class="font-medium">Пока нет Actions</p>
      <p class="mt-2 text-sm text-base-content/60">
        Создайте, например, <span class="font-mono">parse_request</span> или
        <span class="font-mono">clarify_with_foreman</span>
      </p>
      <button type="button" class="btn btn-sm mt-4" @click="openCreate">
        Создать Action
      </button>
    </div>

    <div v-else class="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside class="rounded-2xl border border-base-300 bg-base-100 p-2 shadow-sm">
        <input
          v-model="searchQuery"
          type="search"
          class="input input-bordered input-sm mb-2 w-full"
          placeholder="Поиск по name или id…"
        />

        <p
          v-if="filteredActions.length === 0"
          class="px-2 py-4 text-center text-xs text-base-content/50"
        >
          Ничего не найдено
        </p>

        <button
          v-for="action in filteredActions"
          :key="action.id"
          type="button"
          class="btn btn-sm mb-1 h-auto min-h-0 w-full justify-start py-2 font-normal"
          :class="{ 'btn-active': selectedId === action.id }"
          @click="selectAction(action.id)"
        >
          <span class="min-w-0 flex-1 truncate text-left">
            <span class="block truncate">{{ action.name }}</span>
            <span class="block truncate font-mono text-[10px] opacity-60">{{ action.id }}</span>
            <span class="mt-1 flex flex-wrap gap-1">
              <span
                v-for="badge in actionBadges(action)"
                :key="badge.label"
                class="badge"
                :class="badge.class"
              >
                {{ badge.label }}
              </span>
            </span>
          </span>
        </button>
        <p class="mt-2 px-2 text-[10px] text-base-content/40">
          {{ filteredActions.length }}/{{ actions.length }} ·
          {{ selected ? formatDateTime(selected.updatedAt) : "—" }}
        </p>
      </aside>

      <ActionEditor
        v-if="selected"
        :key="selected.id"
        :agent-slug="agentSlug"
        :action="selected"
        @deleted="selectedId = actions[0]?.id ?? null"
        @action-id-changed="onActionIdChanged"
      />
    </div>

    <dialog class="modal" :class="{ 'modal-open': createOpen }">
      <div class="modal-box">
        <h3 class="text-lg font-semibold">Новый Action</h3>
        <div class="mt-4 space-y-3">
          <label class="form-control w-full">
            <span class="label-text">Название</span>
            <input
              v-model="formName"
              class="input input-bordered w-full"
              placeholder="Parse request"
            />
          </label>
          <label class="form-control w-full">
            <span class="label-text">ID</span>
            <input
              v-model="formId"
              class="input input-bordered w-full font-mono"
              placeholder="parse_request"
              @input="idTouched = true"
            />
          </label>
          <label class="form-control w-full">
            <span class="label-text">Описание</span>
            <textarea
              v-model="formDescription"
              class="textarea textarea-bordered w-full"
              rows="2"
            />
          </label>
          <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
        </div>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" @click="createOpen = false">Отмена</button>
          <button type="button" class="btn" @click="saveCreate">Создать</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @submit.prevent="createOpen = false">
        <button type="submit">close</button>
      </form>
    </dialog>
  </section>
</template>
