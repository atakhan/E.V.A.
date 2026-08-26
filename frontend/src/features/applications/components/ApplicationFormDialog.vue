<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ApplicationForm from "@/features/applications/components/ApplicationForm.vue";
import { useApplications } from "@/features/applications/composables/useApplications";
import type { Application } from "@/features/applications/types/application";
import {
  applicationModulePath,
  defaultModuleSlug,
} from "@/router/paths";

const props = defineProps<{
  application?: Application | null;
  mode: "create" | "edit";
}>();

const emit = defineEmits<{
  saved: [app: Application];
  closed: [];
}>();

const route = useRoute();
const router = useRouter();
const { createApplication, updateApplication, suggestUniqueAppSlug } = useApplications();

const isOpen = ref(false);
const formName = ref("");
const formSlug = ref("");
const formDescription = ref("");
const formError = ref<string | null>(null);
const slugTouched = ref(false);

const title = computed(() =>
  props.mode === "create" ? "Новое приложение" : "Редактировать приложение",
);

const submitLabel = computed(() => (props.mode === "create" ? "Создать" : "Сохранить"));

function resetFromApplication(app: Application | null | undefined) {
  formName.value = app?.name ?? "";
  formSlug.value = app?.slug ?? "";
  formDescription.value = app?.description ?? "";
  formError.value = null;
  slugTouched.value = false;
}

function open() {
  resetFromApplication(props.application);
  if (props.mode === "create") {
    formSlug.value = suggestUniqueAppSlug("app");
  }
  isOpen.value = true;
}

function close() {
  isOpen.value = false;
  formError.value = null;
  emit("closed");
}

watch(
  () => props.application,
  (app) => {
    if (isOpen.value) {
      resetFromApplication(app);
    }
  },
);

watch(formName, (name) => {
  if (props.mode !== "create" || !isOpen.value || slugTouched.value) return;
  formSlug.value = suggestUniqueAppSlug(name || "app");
});

async function save() {
  formError.value = null;

  if (props.mode === "create") {
    const result = createApplication({
      name: formName.value,
      slug: formSlug.value,
      description: formDescription.value,
    });

    if (!result.ok) {
      formError.value = result.error;
      return;
    }

    close();
    emit("saved", result.app);
    await router.push(applicationModulePath(result.app.slug, defaultModuleSlug));
    return;
  }

  if (!props.application) return;

  const previousSlug = props.application.slug;
  const result = updateApplication(props.application.id, {
    name: formName.value,
    slug: formSlug.value,
    description: formDescription.value,
  });

  if (!result.ok) {
    formError.value = result.error;
    return;
  }

  close();
  emit("saved", result.app);

  if (result.app.slug !== previousSlug && route.params.appSlug === previousSlug) {
    const moduleSlug = String(route.params.moduleSlug || defaultModuleSlug);
    await router.replace(applicationModulePath(result.app.slug, moduleSlug));
  }
}

defineExpose({ open, close });
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': isOpen }">
    <div class="modal-box">
      <h3 class="text-lg font-semibold">{{ title }}</h3>

      <div class="mt-4">
        <ApplicationForm
          v-model:name="formName"
          v-model:slug="formSlug"
          v-model:description="formDescription"
          :error="formError"
          @slug-input="slugTouched = true"
        />
      </div>

      <div class="modal-action">
        <button type="button" class="btn btn-ghost" @click="close">Отмена</button>
        <button type="button" class="btn" @click="save">{{ submitLabel }}</button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @submit.prevent="close">
      <button type="submit">close</button>
    </form>
  </dialog>
</template>
