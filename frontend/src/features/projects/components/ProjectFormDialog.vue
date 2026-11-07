<script setup lang="ts">
import { computed, ref } from "vue";
import { useProjects } from "@/features/projects/composables/useProjects";
import type { Project } from "@/features/projects/types/project";

const props = defineProps<{
  mode: "create" | "edit";
  project?: Project | null;
}>();

const emit = defineEmits<{
  saved: [project: Project];
}>();

const { createProject, saveDetails, suggestSlug } = useProjects();

const isOpen = ref(false);
const name = ref("");
const slug = ref("");
const description = ref("");
const error = ref<string | null>(null);
const saving = ref(false);
const slugTouched = ref(false);

const title = computed(() => (props.mode === "create" ? "Новый проект" : "Проект"));

function open() {
  name.value = props.project?.name ?? "";
  slug.value = props.mode === "create" ? suggestSlug("project") : (props.project?.slug ?? "");
  description.value = props.project?.description ?? "";
  error.value = null;
  saving.value = false;
  slugTouched.value = false;
  isOpen.value = true;
}

function close() {
  isOpen.value = false;
}

function onNameInput() {
  if (props.mode === "create" && !slugTouched.value) {
    slug.value = suggestSlug(name.value || "project");
  }
}

async function submit() {
  saving.value = true;
  error.value = null;
  try {
    if (props.mode === "create") {
      const result = await createProject({
        name: name.value,
        slug: slug.value,
        description: description.value,
      });
      if (!result.ok) {
        error.value = result.error;
        return;
      }
      emit("saved", result.project);
      close();
      return;
    }
    if (!props.project) return;
    const project = await saveDetails(props.project.slug, {
      name: name.value,
      description: description.value,
    });
    emit("saved", project);
    close();
  } catch (submitError) {
    error.value = submitError instanceof Error ? submitError.message : "Не удалось сохранить проект";
  } finally {
    saving.value = false;
  }
}

defineExpose({ open, close });
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': isOpen }">
    <form class="modal-box" @submit.prevent="submit">
      <h2 class="text-lg font-semibold">{{ title }}</h2>
      <div class="mt-4 space-y-3">
        <label class="form-control w-full">
          <span class="label-text">Название</span>
          <input v-model="name" class="input input-bordered w-full" @input="onNameInput" />
        </label>
        <label v-if="mode === 'create'" class="form-control w-full">
          <span class="label-text">Адрес</span>
          <input
            v-model="slug"
            class="input input-bordered w-full font-mono"
            @input="slugTouched = true"
          />
        </label>
        <label class="form-control w-full">
          <span class="label-text">Описание</span>
          <textarea v-model="description" class="textarea textarea-bordered w-full" rows="3" />
        </label>
        <p v-if="error" class="text-sm text-error">{{ error }}</p>
      </div>
      <div class="modal-action">
        <button type="button" class="btn btn-ghost" @click="close">Отмена</button>
        <button type="submit" class="btn" :disabled="saving">
          {{ mode === "create" ? "Создать" : "Сохранить" }}
        </button>
      </div>
    </form>
    <form method="dialog" class="modal-backdrop" @submit.prevent="close">
      <button type="submit">закрыть</button>
    </form>
  </dialog>
</template>
