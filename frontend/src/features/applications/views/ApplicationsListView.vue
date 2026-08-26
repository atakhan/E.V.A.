<script setup lang="ts">
import { ref, useTemplateRef } from "vue";
import { useRouter } from "vue-router";
import ApplicationCard from "@/features/applications/components/ApplicationCard.vue";
import ApplicationFormDialog from "@/features/applications/components/ApplicationFormDialog.vue";
import { useApplications } from "@/features/applications/composables/useApplications";
import type { Application } from "@/features/applications/types/application";
import { applicationModulePath, defaultModuleSlug } from "@/router/paths";

const router = useRouter();
const { applications, deleteApplication } = useApplications();

const createDialog = useTemplateRef("createDialog");
const editDialog = useTemplateRef("editDialog");
const editingApplication = ref<Application | null>(null);

function openCreateForm() {
  createDialog.value?.open();
}

function openEditForm(app: Application) {
  editingApplication.value = app;
  editDialog.value?.open();
}

async function openApplication(app: Application) {
  await router.push(applicationModulePath(app.slug, defaultModuleSlug));
}

function removeApplication(app: Application) {
  if (!confirm(`Удалить приложение «${app.name}»?`)) return;
  deleteApplication(app.id);
  editDialog.value?.close();
}
</script>

<template>
  <main class="min-h-screen bg-base-200 px-6 py-10">
    <div class="mx-auto max-w-5xl">
      <header class="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-semibold tracking-wide">E.V.A.</h1>
          <p class="mt-1 text-sm text-base-content/60">Engine for Versatile Agents</p>
          <p class="mt-3 text-base text-base-content/70">Приложения</p>
        </div>
        <button type="button" class="btn" @click="openCreateForm()">
          Новое приложение
        </button>
      </header>

      <div
        v-if="applications.length === 0"
        class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-16 text-center"
      >
        <p class="text-lg font-medium">Пока нет приложений</p>
        <p class="mt-2 text-sm text-base-content/60">
          Приложение объединяет все модули агента: Core, Tools, Memory, Context и Reflection
        </p>
        <button type="button" class="btn mt-6" @click="openCreateForm()">
          Создать приложение
        </button>
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <ApplicationCard
          v-for="app in applications"
          :key="app.id"
          :application="app"
          @open="openApplication(app)"
          @edit="openEditForm(app)"
          @remove="removeApplication(app)"
        />
      </div>
    </div>

    <ApplicationFormDialog ref="createDialog" mode="create" />
    <ApplicationFormDialog
      ref="editDialog"
      mode="edit"
      :application="editingApplication"
    />
  </main>
</template>
