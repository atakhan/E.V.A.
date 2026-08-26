<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useSkills } from "@/features/skills/composables/useSkills";
import { skillPath } from "@/router/paths";
import { formatDateTime } from "@/shared/utils/formatDate";

const props = defineProps<{
  agentSlug: string;
}>();

const router = useRouter();
const { getSkills, createSkill, renameSkill, deleteSkill } = useSkills();

const renamingId = ref<string | null>(null);
const renameValue = ref("");

const skills = computed(() => getSkills(props.agentSlug));

function startRename(skill: { id: string; name: string }) {
  renamingId.value = skill.id;
  renameValue.value = skill.name;
}

function commitRename(id: string) {
  renameSkill(props.agentSlug, id, renameValue.value);
  renamingId.value = null;
}

async function openSkill(id: string) {
  await router.push(skillPath(props.agentSlug, id));
}

async function createAndOpenSkill() {
  const skill = createSkill(props.agentSlug);
  if (!skill) return;
  await router.push(skillPath(props.agentSlug, skill.id));
}
</script>

<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Skills</h2>
        <p class="text-sm text-base-content/60">
          Процессы агента. Каждый Skill — FSM на холсте
        </p>
      </div>
      <button type="button" class="btn btn-sm" @click="createAndOpenSkill()">
        Новый Skill
      </button>
    </div>

    <div
      v-if="skills.length === 0"
      class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-12 text-center"
    >
      <p class="font-medium">Пока нет Skills</p>
      <p class="mt-2 text-sm text-base-content/60">
        Создайте первый Skill, чтобы описать поведение на холсте
      </p>
      <button type="button" class="btn btn-sm mt-4" @click="createAndOpenSkill()">
        Создать Skill
      </button>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="skill in skills"
        :key="skill.id"
        class="card border border-base-300 bg-base-100 shadow-sm transition hover:shadow-md"
      >
        <div class="card-body gap-4">
          <button
            type="button"
            class="aspect-video w-full rounded-xl border border-base-300 bg-base-200/70 transition hover:border-primary/40"
            @click="openSkill(skill.id)"
          >
            <div class="flex h-full items-center justify-center text-xs text-base-content/50">
              {{ skill.states.length }} states
            </div>
          </button>

          <div class="space-y-2">
            <div v-if="renamingId === skill.id" class="join w-full">
              <input
                v-model="renameValue"
                class="input input-sm join-item w-full"
                @keydown.enter="commitRename(skill.id)"
                @keydown.escape="renamingId = null"
              />
              <button type="button" class="btn btn-sm join-item" @click="commitRename(skill.id)">
                OK
              </button>
            </div>
            <button
              v-else
              type="button"
              class="text-left text-base font-medium hover:text-primary"
              @click="openSkill(skill.id)"
            >
              {{ skill.name }}
            </button>

            <p class="text-xs text-base-content/50">
              Обновлено {{ formatDateTime(skill.updatedAt) }}
            </p>
          </div>

          <div class="card-actions justify-end">
            <button type="button" class="btn btn-xs btn-ghost" @click="startRename(skill)">
              Переименовать
            </button>
            <button
              type="button"
              class="btn btn-xs btn-ghost text-error"
              @click="deleteSkill(agentSlug, skill.id)"
            >
              Удалить
            </button>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
