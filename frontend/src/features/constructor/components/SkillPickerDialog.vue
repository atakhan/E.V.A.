<script setup lang="ts">
import { computed } from "vue";
import { useSkills } from "@/features/skills/composables/useSkills";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  agentSlug: string;
  open: boolean;
}>();

const emit = defineEmits<{
  "update:open": [value: boolean];
  select: [skillId: string];
  create: [];
}>();

const { getSkills } = useSkills();

const skills = computed(() => getSkills(props.agentSlug));

function close() {
  emit("update:open", false);
}

function selectSkill(skillId: string) {
  emit("select", skillId);
  close();
}

function createSkill() {
  emit("create");
  close();
}
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': open }">
    <div class="modal-box max-w-lg">
      <h3 class="text-lg font-semibold">Навыки агента</h3>
      <p class="mt-1 text-sm text-base-content/60">
        Все навыки уже на холсте — откройте один или создайте новый
      </p>

      <div class="mt-4 max-h-80 space-y-1 overflow-y-auto">
        <p
          v-if="skills.length === 0"
          class="rounded-box border border-dashed border-base-300 px-4 py-8 text-center text-sm text-base-content/60"
        >
          Пока нет навыков у этого агента
        </p>

        <button
          v-for="skill in skills"
          :key="skill.id"
          type="button"
          class="flex w-full items-center justify-between gap-3 rounded-box border border-base-300 bg-base-200/40 px-4 py-3 text-left transition hover:border-primary/40 hover:bg-base-200"
          @click="selectSkill(skill.id)"
        >
          <span class="min-w-0">
            <span class="block truncate font-medium">{{ skill.name }}</span>
            <span class="mt-0.5 block text-xs text-base-content/50">
              {{ skill.states.length }} states · обновлён {{ formatDateTime(skill.updatedAt) }}
            </span>
          </span>
          <svg
            viewBox="0 0 24 24"
            class="size-4 shrink-0 text-base-content/40"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>
      </div>

      <div class="modal-action flex-wrap">
        <button type="button" class="btn btn-ghost" @click="close">Отмена</button>
        <button type="button" class="btn btn-primary" @click="createSkill">
          Новый навык
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @submit.prevent="close">
      <button type="submit">close</button>
    </form>
  </dialog>
</template>
