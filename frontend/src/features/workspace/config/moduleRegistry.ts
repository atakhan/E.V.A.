import type { Component } from "vue";
import FsmModuleView from "@/features/modules/fsm/views/FsmModuleView.vue";
import ModulePlaceholderPanel from "@/features/workspace/components/ModulePlaceholderPanel.vue";
import { FSM_MODULE_ID } from "@/features/modules/fsm/types/fsmModule";
import type { ModuleSection } from "@/features/workspace/config/modules";

export interface ModuleViewDefinition {
  component: Component;
  usesSectionProps: boolean;
}

const moduleViews: Record<string, ModuleViewDefinition> = {
  [FSM_MODULE_ID]: {
    component: FsmModuleView,
    usesSectionProps: false,
  },
};

export function resolveModuleView(sectionId: string): ModuleViewDefinition {
  return (
    moduleViews[sectionId] ?? {
      component: ModulePlaceholderPanel,
      usesSectionProps: true,
    }
  );
}

export function moduleViewProps(
  sectionId: string,
  section: ModuleSection | undefined,
  appSlug: string,
): Record<string, unknown> {
  const definition = resolveModuleView(sectionId);
  if (definition.usesSectionProps) {
    return { section };
  }
  return { appSlug };
}

export function registerModuleView(sectionId: string, definition: ModuleViewDefinition) {
  moduleViews[sectionId] = definition;
}
