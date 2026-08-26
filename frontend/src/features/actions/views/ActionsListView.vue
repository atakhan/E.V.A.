<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useActions } from "@/features/actions/composables/useActions";
import { normalizeActionId } from "@/features/actions/types/normalize";
import ActionEditor from "@/features/actions/components/ActionEditor.vue";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  agentSlug: string;
}>();

const { getActions, createAction, isActionIdAvailable } = useActions();

const selectedId = ref<string | null>(null);
const createOpen = ref(false);
const formName = ref("");
const formId = ref("");
const formDescription = ref("");
const formError = ref<string | null>(null);
const idTouched = ref(false);

const actions = computed(() => getActions(props.agentSlug));
const selected = computed(
  () => actions.value.find((action) => action.id === selectedId.value) ?? null,
);

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

    <div v-else class="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside class="rounded-2xl border border-base-300 bg-base-100 p-2 shadow-sm">
        <button
          v-for="action in actions"
          :key="action.id"
          type="button"
          class="btn btn-sm mb-1 w-full justify-start font-normal"
          :class="{ 'btn-active': selectedId === action.id }"
          @click="selectedId = action.id"
        >
          <span class="min-w-0 truncate text-left">
            <span class="block truncate">{{ action.name }}</span>
            <span class="block truncate font-mono text-[10px] opacity-60">{{ action.id }}</span>
          </span>
        </button>
        <p class="mt-2 px-2 text-[10px] text-base-content/40">
          {{ actions.length }} ·
          {{ selected ? formatDateTime(selected.updatedAt) : "—" }}
        </p>
      </aside>

      <ActionEditor
        v-if="selected"
        :key="selected.id"
        :agent-slug="agentSlug"
        :action="selected"
        @deleted="selectedId = actions[0]?.id ?? null"
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
