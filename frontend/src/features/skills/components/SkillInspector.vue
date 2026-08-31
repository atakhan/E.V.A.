<script setup lang="ts">
import { computed } from "vue";
import { useActions } from "@/features/actions/composables/useActions";
import type { ActionDef } from "@/features/actions/types/action";
import type { AgentIssue } from "@/features/agents/utils/validateAgent";
import SkillValidationPanel from "@/features/skills/components/SkillValidationPanel.vue";
import type { FsmEditorState, FsmSelection, FsmState } from "@/features/skills/types/fsm";
import { suggestedSkillEvents } from "@/features/skills/utils/skillEvents";

const props = defineProps<{
  agentSlug: string;
  skillVersion?: string;
  skillDescription?: string;
  validationIssues?: AgentIssue[];
  validationOpen?: boolean;
}>();

const emit = defineEmits<{
  "update:skillVersion": [value: string];
  "update:skillDescription": [value: string];
  "update:validationOpen": [value: boolean];
  selectIssue: [issue: AgentIssue];
}>();

const model = defineModel<FsmEditorState>({ required: true });
const selection = defineModel<FsmSelection>("selection", { required: true });

const { getActions } = useActions();
const catalog = computed(() => getActions(props.agentSlug));
const eventSuggestions = computed(() =>
  suggestedSkillEvents(catalog.value.map((action) => action.id)),
);

function addParam() {
  model.value.params.push({ name: "", type: "string", required: false });
}

function removeParam(index: number) {
  model.value.params.splice(index, 1);
}

const selectedState = computed(() => {
  if (selection.value?.kind !== "state") return null;
  return model.value.states.find((state) => state.id === selection.value!.stateId) ?? null;
});

const selectedTransition = computed(() => {
  const current = selection.value;
  if (current?.kind !== "transition") return null;
  const state = model.value.states.find((item) => item.id === current.stateId);
  if (!state) return null;
  const transition = state.transitions.find((item) => item.id === current.transitionId);
  if (!transition) return null;
  return { state, transition };
});

const stateIds = computed(() => model.value.states.map((state) => state.id));

function renameState(state: FsmState, nextId: string) {
  const trimmed = nextId.trim().replace(/\s+/g, "_");
  if (!trimmed || trimmed === state.id) return;
  if (model.value.states.some((item) => item.id === trimmed)) return;

  const previous = state.id;
  state.id = trimmed;
  if (model.value.initial === previous) {
    model.value.initial = trimmed;
  }
  for (const item of model.value.states) {
    for (const transition of item.transitions) {
      if (transition.to === previous) transition.to = trimmed;
    }
  }
  selection.value = { kind: "state", stateId: trimmed };
}

function setInitial(stateId: string) {
  model.value.initial = stateId;
}

function actionLabel(actionId: string): string {
  const action = catalog.value.find((item) => item.id === actionId);
  return action ? `${action.name} (${action.id})` : actionId;
}

function isKnownAction(actionId: string): boolean {
  return catalog.value.some((action) => action.id === actionId);
}

function addActionToList(list: string[], actionId: string) {
  if (!actionId || list.includes(actionId)) return;
  list.push(actionId);
}

function removeActionFromList(list: string[], actionId: string) {
  const index = list.indexOf(actionId);
  if (index === -1) return;
  list.splice(index, 1);
}

function moveActionInList(list: string[], actionId: string, direction: -1 | 1) {
  const index = list.indexOf(actionId);
  const next = index + direction;
  if (index < 0 || next < 0 || next >= list.length) return;
  const [item] = list.splice(index, 1);
  list.splice(next, 0, item);
}

function availableToAdd(list: string[]): ActionDef[] {
  return catalog.value.filter((action) => !list.includes(action.id));
}
</script>

<template>
  <aside class="flex h-full w-80 shrink-0 flex-col border-l border-base-300 bg-base-100">
    <div class="border-b border-base-300 px-4 py-3">
      <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Inspector</p>
      <p class="mt-1 text-sm text-base-content/70">
        <template v-if="selectedState">State</template>
        <template v-else-if="selectedTransition">Transition</template>
        <template v-else>Ничего не выбрано</template>
      </p>
    </div>

    <div class="flex-1 space-y-4 overflow-y-auto p-4">
      <template v-if="selectedState">
        <label class="form-control w-full">
          <span class="label-text">Название</span>
          <input
            v-model="selectedState.name"
            class="input input-bordered input-sm w-full"
            placeholder="Например: Ожидание сообщения"
          />
          <span class="label-text-alt text-base-content/50">
            Отображается на холсте; технический id — ниже
          </span>
        </label>

        <label class="form-control w-full">
          <span class="label-text">State id</span>
          <input
            class="input input-bordered input-sm w-full font-mono"
            :value="selectedState.id"
            @change="renameState(selectedState, ($event.target as HTMLInputElement).value)"
          />
        </label>

        <div class="space-y-2">
          <p class="label-text">on_enter (Actions)</p>
          <ul v-if="selectedState.onEnter.length" class="space-y-1">
            <li
              v-for="actionId in selectedState.onEnter"
              :key="actionId"
              class="flex items-center gap-1 rounded-lg border border-base-300 bg-base-200/40 px-2 py-1"
            >
              <span
                class="min-w-0 flex-1 truncate font-mono text-xs"
                :class="{ 'text-warning': !isKnownAction(actionId) }"
                :title="actionLabel(actionId)"
              >
                {{ actionId }}
              </span>
              <button
                type="button"
                class="btn btn-ghost btn-xs"
                @click="moveActionInList(selectedState.onEnter, actionId, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn btn-ghost btn-xs"
                @click="moveActionInList(selectedState.onEnter, actionId, 1)"
              >
                ↓
              </button>
              <button
                type="button"
                class="btn btn-ghost btn-xs text-error"
                @click="removeActionFromList(selectedState.onEnter, actionId)"
              >
                ×
              </button>
            </li>
          </ul>
          <p v-else class="text-xs text-base-content/50">Нет actions на входе</p>
          <select
            class="select select-bordered select-sm w-full"
            :disabled="availableToAdd(selectedState.onEnter).length === 0"
            @change="
              addActionToList(selectedState.onEnter, ($event.target as HTMLSelectElement).value);
              ($event.target as HTMLSelectElement).value = '';
            "
          >
            <option value="">
              {{
                catalog.length === 0
                  ? "Сначала создайте Action"
                  : availableToAdd(selectedState.onEnter).length === 0
                    ? "Все Actions уже добавлены"
                    : "Добавить Action…"
              }}
            </option>
            <option
              v-for="action in availableToAdd(selectedState.onEnter)"
              :key="action.id"
              :value="action.id"
            >
              {{ action.name }} ({{ action.id }})
            </option>
          </select>
        </div>

        <label class="label cursor-pointer justify-start gap-3">
          <input
            v-model="selectedState.final"
            type="checkbox"
            class="checkbox checkbox-sm"
          />
          <span class="label-text">final</span>
        </label>

        <button
          type="button"
          class="btn btn-sm w-full"
          :class="{ 'btn-primary': model.initial === selectedState.id }"
          @click="setInitial(selectedState.id)"
        >
          {{ model.initial === selectedState.id ? "Initial state" : "Сделать initial" }}
        </button>
      </template>

      <template v-else-if="selectedTransition">
        <label class="form-control w-full">
          <span class="label-text">Event</span>
          <input
            v-model="selectedTransition.transition.event"
            class="input input-bordered input-sm w-full font-mono"
            placeholder="channel.message.received"
            list="skill-event-suggestions"
          />
        </label>

        <label class="form-control w-full">
          <span class="label-text">Guard</span>
          <input
            v-model="selectedTransition.transition.guard"
            class="input input-bordered input-sm w-full font-mono"
            placeholder="optional expression"
          />
        </label>

        <div class="space-y-2">
          <p class="label-text">Actions</p>
          <ul v-if="selectedTransition.transition.actions.length" class="space-y-1">
            <li
              v-for="actionId in selectedTransition.transition.actions"
              :key="actionId"
              class="flex items-center gap-1 rounded-lg border border-base-300 bg-base-200/40 px-2 py-1"
            >
              <span
                class="min-w-0 flex-1 truncate font-mono text-xs"
                :class="{ 'text-warning': !isKnownAction(actionId) }"
                :title="actionLabel(actionId)"
              >
                {{ actionId }}
              </span>
              <button
                type="button"
                class="btn btn-ghost btn-xs"
                @click="moveActionInList(selectedTransition.transition.actions, actionId, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn btn-ghost btn-xs"
                @click="moveActionInList(selectedTransition.transition.actions, actionId, 1)"
              >
                ↓
              </button>
              <button
                type="button"
                class="btn btn-ghost btn-xs text-error"
                @click="removeActionFromList(selectedTransition.transition.actions, actionId)"
              >
                ×
              </button>
            </li>
          </ul>
          <p v-else class="text-xs text-base-content/50">Нет actions на переходе</p>
          <select
            class="select select-bordered select-sm w-full"
            :disabled="availableToAdd(selectedTransition.transition.actions).length === 0"
            @change="
              addActionToList(
                selectedTransition.transition.actions,
                ($event.target as HTMLSelectElement).value,
              );
              ($event.target as HTMLSelectElement).value = '';
            "
          >
            <option value="">
              {{
                catalog.length === 0
                  ? "Сначала создайте Action"
                  : availableToAdd(selectedTransition.transition.actions).length === 0
                    ? "Все Actions уже добавлены"
                    : "Добавить Action…"
              }}
            </option>
            <option
              v-for="action in availableToAdd(selectedTransition.transition.actions)"
              :key="action.id"
              :value="action.id"
            >
              {{ action.name }} ({{ action.id }})
            </option>
          </select>
        </div>

        <label class="form-control w-full">
          <span class="label-text">to</span>
          <select
            v-model="selectedTransition.transition.to"
            class="select select-bordered select-sm w-full"
          >
            <option v-for="id in stateIds" :key="id" :value="id">{{ id }}</option>
          </select>
        </label>

        <p class="text-xs text-base-content/50">
          from: <span class="font-mono">{{ selectedTransition.state.id }}</span>
        </p>
      </template>

      <template v-else>
        <p class="text-sm text-base-content/60">
          Выберите state или transition. Actions берутся из каталога агента (раздел Actions).
        </p>

        <label class="form-control w-full">
          <span class="label-text">Version (SemVer)</span>
          <input
            class="input input-bordered input-sm w-full font-mono"
            :value="skillVersion ?? '0.1.0'"
            placeholder="1.0.0"
            @input="emit('update:skillVersion', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="form-control w-full">
          <span class="label-text">Description</span>
          <textarea
            class="textarea textarea-bordered textarea-sm w-full"
            rows="2"
            :value="skillDescription ?? ''"
            @input="emit('update:skillDescription', ($event.target as HTMLTextAreaElement).value)"
          />
        </label>

        <div class="space-y-2">
          <div class="flex items-center justify-between gap-2">
            <p class="label-text">Params</p>
            <button type="button" class="btn btn-xs" @click="addParam">Добавить</button>
          </div>
          <div
            v-if="model.params.length === 0"
            class="rounded-lg border border-dashed border-base-300 px-3 py-4 text-xs text-base-content/50"
          >
            Нет параметров Skill
          </div>
          <div
            v-for="(param, index) in model.params"
            :key="`${param.name}-${index}`"
            class="rounded-lg border border-base-300 bg-base-200/40 p-2 space-y-2"
          >
            <div class="flex gap-2">
              <input
                v-model="param.name"
                class="input input-bordered input-xs flex-1 font-mono"
                placeholder="request_id"
              />
              <select v-model="param.type" class="select select-bordered select-xs">
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="boolean">boolean</option>
                <option value="object">object</option>
                <option value="array">array</option>
              </select>
              <button type="button" class="btn btn-xs btn-ghost text-error" @click="removeParam(index)">
                ×
              </button>
            </div>
            <label class="label cursor-pointer justify-start gap-2 py-0">
              <input v-model="param.required" type="checkbox" class="checkbox checkbox-xs" />
              <span class="label-text text-xs">required</span>
            </label>
          </div>
        </div>

        <div class="rounded-xl border border-dashed border-base-300 bg-base-200/40 p-3 text-xs text-base-content/60">
          <p>initial: <span class="font-mono">{{ model.initial ?? "—" }}</span></p>
          <p class="mt-1">states: {{ model.states.length }}</p>
          <p class="mt-1">actions in catalog: {{ catalog.length }}</p>
        </div>
      </template>
    </div>

    <datalist id="skill-event-suggestions">
      <option v-for="eventName in eventSuggestions" :key="eventName" :value="eventName" />
    </datalist>

    <div class="border-t border-base-300 p-3">
      <button
        type="button"
        class="flex w-full items-center justify-between text-left text-xs font-semibold uppercase tracking-wide text-base-content/50"
        @click="emit('update:validationOpen', !validationOpen)"
      >
        <span>Validation</span>
        <span class="font-mono normal-case">
          {{ validationIssues?.length ?? 0 }}
          <span class="text-base-content/40">{{ validationOpen ? "▾" : "▸" }}</span>
        </span>
      </button>
      <div v-if="validationOpen !== false" class="mt-2 max-h-48 overflow-y-auto">
        <SkillValidationPanel
          :agent-slug="agentSlug"
          :issues="validationIssues ?? []"
          :selection="selection"
          compact
          @select-issue="emit('selectIssue', $event)"
        />
      </div>
    </div>
  </aside>
</template>
