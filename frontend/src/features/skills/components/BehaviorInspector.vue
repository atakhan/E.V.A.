<script setup lang="ts">
import { computed } from "vue";
import { useActions } from "@/features/actions/composables/useActions";
import type { AgentIssue } from "@/features/agents/utils/validateAgent";
import SkillValidationPanel from "@/features/skills/components/SkillValidationPanel.vue";
import type {
  BehaviorGraph,
  BehaviorNode,
  BehaviorSelection,
  ExecutionArtifact,
} from "@/features/skills/types/behavior";
import type { SkillParam } from "@/features/skills/types/fsm";
import { COMMON_DOMAIN_EVENTS } from "@/features/skills/utils/skillEvents";
import { createId } from "@/shared/utils/id";

const props = defineProps<{
  agentSlug: string;
  skillVersion?: string;
  skillDescription?: string;
  validationIssues?: AgentIssue[];
  validationOpen?: boolean;
  execution?: ExecutionArtifact | null;
  compileError?: string | null;
}>();

const emit = defineEmits<{
  "update:skillVersion": [value: string];
  "update:skillDescription": [value: string];
  "update:validationOpen": [value: boolean];
  selectIssue: [issue: AgentIssue];
  showMachine: [];
}>();

const model = defineModel<BehaviorGraph>({ required: true });
const params = defineModel<SkillParam[]>("params", { required: true });
const selection = defineModel<BehaviorSelection>("selection", { required: true });

const { getActions } = useActions();
const catalog = computed(() => getActions(props.agentSlug));

const selectedNode = computed(() => {
  const current = selection.value;
  if (current?.kind !== "node" && current?.kind !== "branch") return null;
  return model.value.nodes.find((node) => node.id === current.nodeId) ?? null;
});

function patchNode(nodeId: string, patch: Partial<BehaviorNode>) {
  model.value = {
    ...model.value,
    nodes: model.value.nodes.map((node) =>
      node.id === nodeId ? ({ ...node, ...patch } as BehaviorNode) : node,
    ),
  };
}

function setWaitType(node: Extract<BehaviorNode, { type: "wait" }>, type: string) {
  if (type === "event") {
    patchNode(node.id, { waitFor: { type: "event", event: "channel.message.received" } } as Partial<BehaviorNode>);
  } else if (type === "action") {
    patchNode(node.id, {
      waitFor: { type: "action", actionId: catalog.value[0]?.id ?? "" },
    } as Partial<BehaviorNode>);
  } else if (type === "condition") {
    patchNode(node.id, {
      waitFor: { type: "condition", event: "channel.message.received", expression: "" },
    } as Partial<BehaviorNode>);
  } else {
    patchNode(node.id, {
      waitFor: { type: "input", event: "channel.message.received" },
    } as Partial<BehaviorNode>);
  }
}

function addBranch(node: Extract<BehaviorNode, { type: "decide" }>) {
  const targets = model.value.nodes.filter((item) => item.id !== node.id && item.type !== "decide");
  patchNode(node.id, {
    branches: [
      ...node.branches,
      {
        id: `edge_${createId()}`,
        label: node.branches.length === 0 ? "Да" : "Нет",
        guard: "",
        to: targets[0]?.id ?? "",
      },
    ],
  } as Partial<BehaviorNode>);
}

function patchBranch(
  node: Extract<BehaviorNode, { type: "decide" }>,
  branchId: string,
  patch: Partial<{ label: string; guard: string; to: string }>,
) {
  patchNode(node.id, {
    branches: node.branches.map((branch) =>
      branch.id === branchId ? { ...branch, ...patch } : branch,
    ),
  } as Partial<BehaviorNode>);
}

function removeBranch(node: Extract<BehaviorNode, { type: "decide" }>, branchId: string) {
  patchNode(node.id, {
    branches: node.branches.filter((branch) => branch.id !== branchId),
  } as Partial<BehaviorNode>);
}

function patchSelectedDecide(branchId: string, patch: Partial<{ label: string; guard: string; to: string }>) {
  const node = selectedNode.value;
  if (node?.type !== "decide") return;
  patchBranch(node, branchId, patch);
}

function removeSelectedBranch(branchId: string) {
  const node = selectedNode.value;
  if (node?.type !== "decide") return;
  removeBranch(node, branchId);
}

function addParam() {
  params.value = [...params.value, { name: "", type: "string", required: false }];
}

function removeParam(index: number) {
  params.value = params.value.filter((_, item) => item !== index);
}

function humanKind(node: BehaviorNode): string {
  if (node.type === "wait") return "Когда / жду";
  if (node.type === "do") return "Я делаю";
  if (node.type === "decide") return "Если";
  return "Задача завершена";
}

const outgoingTo = computed(() => {
  const node = selectedNode.value;
  if (!node || node.type === "decide" || node.type === "end") return "";
  return model.value.edges.find((edge) => edge.from === node.id)?.to ?? "";
});

function setOutgoing(to: string) {
  const node = selectedNode.value;
  if (!node || node.type === "decide" || node.type === "end") return;
  const rest = model.value.edges.filter((edge) => edge.from !== node.id);
  if (!to) {
    model.value = { ...model.value, edges: rest };
    return;
  }
  rest.push({
    id: `edge_${createId()}`,
    from: node.id,
    to,
    kind: to === model.value.entry ? "loop" : "next",
  });
  model.value = { ...model.value, edges: rest };
}

function nodeLabel(node: BehaviorNode): string {
  if (node.type === "decide") return node.question || node.title || node.id;
  return node.title || node.id;
}
</script>

<template>
  <aside class="flex h-full w-80 shrink-0 flex-col border-l border-base-300 bg-base-100">
    <div class="border-b border-base-300 px-4 py-3">
      <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Шаг</p>
      <p class="mt-1 text-sm text-base-content/70">
        <template v-if="selectedNode">{{ humanKind(selectedNode) }}</template>
        <template v-else>Сценарий</template>
      </p>
    </div>

    <div class="flex-1 space-y-4 overflow-y-auto p-4">
      <template v-if="selectedNode?.type === 'wait'">
        <label class="form-control w-full">
          <span class="label-text">Когда</span>
          <input v-model="selectedNode.title" class="input input-bordered input-sm w-full" />
        </label>
        <label class="form-control w-full">
          <span class="label-text">Жду</span>
          <select
            class="select select-bordered select-sm w-full"
            :value="selectedNode.waitFor.type"
            @change="setWaitType(selectedNode, ($event.target as HTMLSelectElement).value)"
          >
            <option value="input">ответ человека</option>
            <option value="event">событие</option>
            <option value="action">завершение действия</option>
            <option value="condition">условие</option>
          </select>
        </label>
        <label v-if="selectedNode.waitFor.type === 'event'" class="form-control w-full">
          <span class="label-text">Событие</span>
          <input
            class="input input-bordered input-sm w-full font-mono"
            :value="selectedNode.waitFor.event"
            list="domain-events"
            @change="
              patchNode(selectedNode.id, {
                waitFor: { type: 'event', event: ($event.target as HTMLInputElement).value },
              } as Partial<BehaviorNode>)
            "
          />
        </label>
        <label v-if="selectedNode.waitFor.type === 'input'" class="form-control w-full">
          <span class="label-text">Событие входа</span>
          <input
            class="input input-bordered input-sm w-full font-mono"
            :value="selectedNode.waitFor.event || 'channel.message.received'"
            @change="
              patchNode(selectedNode.id, {
                waitFor: { type: 'input', event: ($event.target as HTMLInputElement).value },
              } as Partial<BehaviorNode>)
            "
          />
        </label>
        <label v-if="selectedNode.waitFor.type === 'action'" class="form-control w-full">
          <span class="label-text">Action</span>
          <select
            class="select select-bordered select-sm w-full"
            :value="selectedNode.waitFor.actionId"
            @change="
              patchNode(selectedNode.id, {
                waitFor: { type: 'action', actionId: ($event.target as HTMLSelectElement).value },
              } as Partial<BehaviorNode>)
            "
          >
            <option v-for="action in catalog" :key="action.id" :value="action.id">
              {{ action.name }} ({{ action.id }})
            </option>
          </select>
        </label>
        <template v-if="selectedNode.waitFor.type === 'condition'">
          <label class="form-control w-full">
            <span class="label-text">Событие</span>
            <input
              class="input input-bordered input-sm w-full font-mono"
              :value="selectedNode.waitFor.event"
              @change="
                patchNode(selectedNode.id, {
                  waitFor: {
                    type: 'condition',
                    event: ($event.target as HTMLInputElement).value,
                    expression: selectedNode.waitFor.type === 'condition' ? selectedNode.waitFor.expression : '',
                  },
                } as Partial<BehaviorNode>)
              "
            />
          </label>
          <label class="form-control w-full">
            <span class="label-text">Пока истинно</span>
            <input
              class="input input-bordered input-sm w-full font-mono"
              :value="selectedNode.waitFor.expression"
              @change="
                patchNode(selectedNode.id, {
                  waitFor: {
                    type: 'condition',
                    event: selectedNode.waitFor.type === 'condition' ? selectedNode.waitFor.event : 'event',
                    expression: ($event.target as HTMLInputElement).value,
                  },
                } as Partial<BehaviorNode>)
              "
            />
          </label>
        </template>
      </template>

      <template v-else-if="selectedNode?.type === 'do'">
        <label class="form-control w-full">
          <span class="label-text">Я</span>
          <input v-model="selectedNode.title" class="input input-bordered input-sm w-full" />
        </label>
        <label class="form-control w-full">
          <span class="label-text">Действие</span>
          <select v-model="selectedNode.actionId" class="select select-bordered select-sm w-full">
            <option value="">Выберите Action…</option>
            <option v-for="action in catalog" :key="action.id" :value="action.id">
              {{ action.name }} ({{ action.id }})
            </option>
          </select>
        </label>
      </template>

      <template v-else-if="selectedNode?.type === 'decide'">
        <label class="form-control w-full">
          <span class="label-text">Если</span>
          <input v-model="selectedNode.question" class="input input-bordered input-sm w-full" />
        </label>
        <div class="space-y-2">
          <p class="label-text">Ветки</p>
          <div
            v-for="branch in selectedNode.branches"
            :key="branch.id"
            class="space-y-1 rounded-box border border-base-300 p-2"
          >
            <input
              class="input input-bordered input-xs w-full"
              :value="branch.label"
              placeholder="Да / Нет"
              @change="
                patchSelectedDecide(branch.id, {
                  label: ($event.target as HTMLInputElement).value,
                })
              "
            />
            <input
              class="input input-bordered input-xs w-full font-mono"
              :value="branch.guard"
              placeholder="results.length > 1"
              @change="
                patchSelectedDecide(branch.id, {
                  guard: ($event.target as HTMLInputElement).value,
                })
              "
            />
            <select
              class="select select-bordered select-xs w-full"
              :value="branch.to"
              @change="
                patchSelectedDecide(branch.id, {
                  to: ($event.target as HTMLSelectElement).value,
                })
              "
            >
              <option
                v-for="item in model.nodes.filter((n) => n.id !== selectedNode?.id)"
                :key="item.id"
                :value="item.id"
              >
                {{ item.title || item.id }}
              </option>
            </select>
            <button
              type="button"
              class="btn btn-ghost btn-xs"
              @click="removeSelectedBranch(branch.id)"
            >
              Удалить ветку
            </button>
          </div>
          <button type="button" class="btn btn-sm w-full" @click="addBranch(selectedNode)">
            Добавить ветку
          </button>
        </div>
      </template>

      <template v-else-if="selectedNode?.type === 'end'">
        <label class="form-control w-full">
          <span class="label-text">Задача завершена</span>
          <input v-model="selectedNode.title" class="input input-bordered input-sm w-full" />
        </label>
      </template>

      <label
        v-if="selectedNode && selectedNode.type !== 'end' && selectedNode.type !== 'decide'"
        class="form-control w-full"
      >
        <span class="label-text">После этого</span>
        <select
          class="select select-bordered select-sm w-full"
          :value="outgoingTo"
          @change="setOutgoing(($event.target as HTMLSelectElement).value)"
        >
          <option value="">не связано</option>
          <option
            v-for="item in model.nodes.filter((node) => node.id !== selectedNode?.id)"
            :key="item.id"
            :value="item.id"
          >
            {{ nodeLabel(item) }}{{ item.id === model.entry ? " (снова)" : "" }}
          </option>
        </select>
      </label>

      <template v-else>
        <label class="form-control w-full">
          <span class="label-text">Version</span>
          <input
            class="input input-bordered input-sm w-full font-mono"
            :value="skillVersion"
            @change="emit('update:skillVersion', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label class="form-control w-full">
          <span class="label-text">Описание</span>
          <textarea
            class="textarea textarea-bordered textarea-sm w-full"
            :value="skillDescription"
            @change="emit('update:skillDescription', ($event.target as HTMLTextAreaElement).value)"
          />
        </label>
        <div class="space-y-2">
          <p class="label-text">Params</p>
          <div v-for="(param, index) in params" :key="index" class="flex gap-1">
            <input v-model="param.name" class="input input-bordered input-xs flex-1" placeholder="name" />
            <button type="button" class="btn btn-ghost btn-xs" @click="removeParam(index)">×</button>
          </div>
          <button type="button" class="btn btn-sm w-full" @click="addParam">Добавить param</button>
        </div>
        <label class="form-control w-full">
          <span class="label-text">Вход сценария</span>
          <select v-model="model.entry" class="select select-bordered select-sm w-full">
            <option value="">не задан</option>
            <option
              v-for="node in model.nodes.filter((item) => item.type === 'wait')"
              :key="node.id"
              :value="node.id"
            >
              {{ node.title || node.id }}
            </option>
          </select>
        </label>
      </template>

      <div v-if="selectedNode" class="collapse collapse-arrow border border-base-300">
        <input type="checkbox" />
        <div class="collapse-title text-sm font-medium">Технические детали</div>
        <div class="collapse-content space-y-1 text-xs">
          <p class="font-mono">id: {{ selectedNode.id }}</p>
          <p v-if="selectedNode.type === 'do'" class="font-mono">actionId: {{ selectedNode.actionId }}</p>
          <p v-if="selectedNode.type === 'wait'" class="font-mono">
            waitFor: {{ JSON.stringify(selectedNode.waitFor) }}
          </p>
        </div>
      </div>

      <div class="collapse collapse-arrow border border-base-300">
        <input type="checkbox" />
        <div class="collapse-title text-sm font-medium">Машина (read-only)</div>
        <div class="collapse-content space-y-2 text-xs">
          <p v-if="compileError" class="text-error">{{ compileError }}</p>
          <p v-else-if="execution" class="text-base-content/60">
            compiler {{ execution.compilerVersion }} · initial {{ execution.initial }}
          </p>
          <ul v-if="execution" class="space-y-1 font-mono">
            <li v-for="state in execution.states" :key="state.id">
              {{ state.id }} ← {{ state.originNodeId }}
              <span v-for="tr in state.transitions" :key="tr.id" class="block pl-2 text-base-content/50">
                {{ tr.event }} / {{ tr.actions.join(",") }} → {{ tr.to }}
              </span>
            </li>
          </ul>
          <button
            v-if="execution"
            type="button"
            class="btn btn-xs mt-2"
            @click="emit('showMachine')"
          >
            Холст машины
          </button>
        </div>
      </div>
    </div>

    <SkillValidationPanel
      class="border-t border-base-300"
      :agent-slug="agentSlug"
      :issues="validationIssues ?? []"
      compact
      @select-issue="emit('selectIssue', $event)"
    />

    <datalist id="domain-events">
      <option v-for="event in COMMON_DOMAIN_EVENTS" :key="event" :value="event" />
    </datalist>
  </aside>
</template>
