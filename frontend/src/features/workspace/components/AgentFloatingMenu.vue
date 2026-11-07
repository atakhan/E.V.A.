<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from "vue";
import type { WorkspaceSection } from "@/features/workspace/config/nav";
import { findWorkspaceSection, workspaceSections } from "@/features/workspace/config/nav";

const props = defineProps<{
  agentName: string;
  agentSlug: string;
  activeSectionId: string;
}>();

const emit = defineEmits<{
  select: [id: string];
  edit: [];
}>();

const menuOpen = ref(false);
const rootEl = useTemplateRef<HTMLElement>("root");

const activeSection = computed(
  () => findWorkspaceSection(props.activeSectionId) ?? workspaceSections[0],
);

function onDocumentPointerDown(event: PointerEvent) {
  if (!menuOpen.value) return;
  const target = event.target;
  if (target instanceof Node && rootEl.value?.contains(target)) return;
  menuOpen.value = false;
}

function selectSection(section: WorkspaceSection) {
  menuOpen.value = false;
  emit("select", section.id);
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
});
</script>

<template>
  <div ref="root" class="pointer-events-auto relative">
    <div
      class="flex max-w-72 items-center gap-1 rounded-box border border-base-300/60 bg-base-100/90 p-1.5 shadow-lg backdrop-blur-sm"
    >
      <button
        type="button"
        class="btn btn-sm h-auto min-h-0 flex-1 justify-start gap-2 px-2 py-1.5 font-normal"
        :aria-expanded="menuOpen"
        aria-haspopup="menu"
        aria-controls="agent-section-menu"
        @click="menuOpen = !menuOpen"
      >
        <span class="min-w-0 flex-1 text-left">
          <span class="block truncate text-sm font-semibold leading-tight">{{ agentName }}</span>
          <span class="block truncate text-[11px] leading-tight text-base-content/50">
            {{ activeSection.title }}
            <span class="font-mono">/{{ agentSlug }}</span>
          </span>
        </span>
        <svg
          viewBox="0 0 24 24"
          class="size-3.5 shrink-0 text-base-content/50 transition-transform"
          :class="{ 'rotate-180': menuOpen }"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      <button
        type="button"
        class="btn btn-sm btn-square btn-ghost shrink-0"
        title="Редактировать агента"
        aria-label="Редактировать агента"
        @click="emit('edit')"
      >
        ✎
      </button>
    </div>

    <div
      v-if="menuOpen"
      id="agent-section-menu"
      role="menu"
      aria-label="Разделы агента"
      class="absolute left-0 top-full z-50 mt-2 min-w-full rounded-box border border-base-300 bg-base-100 p-1.5 shadow-xl"
    >
      <button
        v-for="section in workspaceSections"
        :key="section.id"
        type="button"
        role="menuitem"
        class="btn btn-sm w-full justify-start font-normal"
        :class="{ 'btn-active': activeSectionId === section.id }"
        @click="selectSection(section)"
      >
        {{ section.title }}
      </button>
    </div>
  </div>
</template>
