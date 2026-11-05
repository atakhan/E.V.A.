<script setup lang="ts">
import { onMounted, useTemplateRef } from "vue";
import { useRouter } from "vue-router";
import ProjectFormDialog from "@/features/projects/components/ProjectFormDialog.vue";
import { useProjects } from "@/features/projects/composables/useProjects";
import type { Project } from "@/features/projects/types/project";
import { projectPath } from "@/router/paths";
import AppMainNav from "@/shared/layout/AppMainNav.vue";

const router = useRouter();
const { projects, refresh, removeProject } = useProjects();
const createDialog = useTemplateRef("createDialog");

onMounted(() => {
  void refresh();
});

async function openProject(project: Project) {
  await router.push(projectPath(project.slug));
}

async function onCreated(project: Project) {
  await router.push(projectPath(project.slug));
}

function remove(project: Project) {
  if (!confirm(`Удалить проект «${project.name}»? Агенты останутся в библиотеке.`)) return;
  void removeProject(project.slug);
}
</script>

<template>
  <div class="px-6 py-8 pb-24 lg:px-8">
    <AppMainNav class="mb-10" />

    <div class="mx-auto max-w-5xl">
      <header class="mb-8">
        <h1 class="text-2xl font-semibold tracking-wide">Проекты</h1>
        <p class="mt-1 text-sm text-base-content/60">
          Стол подключённых агентов и рантайм их общей работы
        </p>
      </header>

      <div
        v-if="projects.length === 0"
        class="rounded-2xl border border-dashed border-base-300 bg-base-100 px-6 py-16 text-center"
      >
        <p class="text-lg font-medium">Пока нет проектов</p>
        <p class="mt-2 text-sm text-base-content/60">
          Проект собирает агентов из библиотеки за одним столом.
        </p>
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="project in projects"
          :key="project.id"
          class="card border border-base-300 bg-base-100 shadow-sm"
        >
          <div class="card-body gap-3">
            <button type="button" class="text-left" @click="openProject(project)">
              <h2 class="text-lg font-semibold">{{ project.name }}</h2>
              <p class="mt-1 font-mono text-xs text-base-content/50">/projects/{{ project.slug }}</p>
              <p class="mt-2 line-clamp-2 text-sm text-base-content/60">
                {{ project.description || "Без описания" }}
              </p>
              <p class="mt-3 text-xs text-base-content/50">
                {{ project.agents.length }} на столе
              </p>
            </button>
            <div class="card-actions justify-end">
              <button type="button" class="btn btn-xs btn-ghost text-error" @click="remove(project)">
                Удалить
              </button>
            </div>
          </div>
        </article>
      </div>
    </div>

    <ProjectFormDialog ref="createDialog" mode="create" @saved="onCreated" />

    <div class="fab">
      <div class="tooltip tooltip-left" data-tip="Новый проект">
        <button
          type="button"
          class="btn btn-lg btn-circle btn-primary shadow-lg"
          aria-label="Новый проект"
          @click="createDialog?.open()"
        >
          <svg viewBox="0 0 24 24" class="size-6" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path stroke-linecap="round" d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>
