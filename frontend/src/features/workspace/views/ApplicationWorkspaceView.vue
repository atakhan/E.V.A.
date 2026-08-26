<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { useRouter } from "vue-router";
import ApplicationFormDialog from "@/features/applications/components/ApplicationFormDialog.vue";
import { useApplications } from "@/features/applications/composables/useApplications";
import {
  moduleViewProps,
  resolveModuleView,
} from "@/features/workspace/config/moduleRegistry";
import {
  findModuleSection,
  moduleSections,
} from "@/features/workspace/config/modules";
import WorkspaceSidebar from "@/features/workspace/components/WorkspaceSidebar.vue";
import {
  applicationModulePathBySection,
  applicationsPath,
  sectionIdFromSlug,
} from "@/router/paths";

const props = defineProps<{
  appSlug: string;
  moduleSlug: string;
}>();

const router = useRouter();
const { getApplicationBySlug } = useApplications();
const editDialog = useTemplateRef("editDialog");

const application = computed(() => getApplicationBySlug(props.appSlug));
const activeSectionId = computed(() => sectionIdFromSlug(props.moduleSlug) ?? "core.fsm");
const activeSection = computed(() => findModuleSection(activeSectionId.value));
const moduleView = computed(() => resolveModuleView(activeSectionId.value));
const moduleComponentProps = computed(() =>
  moduleViewProps(activeSectionId.value, activeSection.value, props.appSlug),
);

async function selectSection(id: string) {
  if (!application.value) return;
  await router.push(applicationModulePathBySection(application.value.slug, id));
}

async function goToApplications() {
  await router.push(applicationsPath());
}
</script>

<template>
  <div v-if="application" class="flex min-h-screen bg-base-200">
    <aside class="flex w-64 shrink-0 flex-col border-r border-base-300 bg-base-100">
      <div class="border-b border-base-300 px-4 py-4">
        <button
          type="button"
          class="btn btn-xs btn-ghost mb-3 -ml-2"
          @click="goToApplications()"
        >
          ← Приложения
        </button>

        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h1 class="truncate text-lg font-semibold">{{ application.name }}</h1>
            <p class="mt-1 font-mono text-xs text-base-content/50">/{{ application.slug }}</p>
            <p
              v-if="application.description"
              class="mt-1 line-clamp-2 text-xs text-base-content/60"
            >
              {{ application.description }}
            </p>
          </div>
          <button
            type="button"
            class="btn btn-xs btn-square btn-ghost shrink-0"
            title="Редактировать приложение"
            aria-label="Редактировать приложение"
            @click="editDialog?.open()"
          >
            ✎
          </button>
        </div>
      </div>

      <WorkspaceSidebar
        :sections="moduleSections"
        :active-id="activeSectionId"
        @select="selectSection"
      />
    </aside>

    <main class="min-w-0 flex-1 overflow-y-auto p-6 lg:p-8">
      <component :is="moduleView.component" v-bind="moduleComponentProps" />
    </main>

    <ApplicationFormDialog
      ref="editDialog"
      mode="edit"
      :application="application"
    />
  </div>
</template>
