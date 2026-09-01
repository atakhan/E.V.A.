import { createRouter, createWebHistory } from "vue-router";
import AgentsListView from "@/features/agents/views/AgentsListView.vue";
import AgentOverviewView from "@/features/agents/views/AgentOverviewView.vue";
import ActionsListView from "@/features/actions/views/ActionsListView.vue";
import ToolsListView from "@/features/tools/views/ToolsListView.vue";
import ToolLibraryView from "@/features/tools/views/ToolLibraryView.vue";
import ToolInstanceEditorView from "@/features/tools/views/ToolInstanceEditorView.vue";
import ToolLogsView from "@/features/tools/views/ToolLogsView.vue";
import SkillsListView from "@/features/skills/views/SkillsListView.vue";
import SkillsSectionLayout from "@/features/skills/views/SkillsSectionLayout.vue";
import SkillCanvasEditorView from "@/features/skills/views/SkillCanvasEditorView.vue";
import AgentRuntimeView from "@/features/runtime/views/AgentRuntimeView.vue";
import GlobalRuntimeView from "@/features/runtime/views/GlobalRuntimeView.vue";
import RuntimeSimulateView from "@/features/runtime/views/RuntimeSimulateView.vue";
import SkillRunDetailView from "@/features/runtime/views/SkillRunDetailView.vue";
import AgentWorkspaceView from "@/features/workspace/views/AgentWorkspaceView.vue";
import AppShellLayout from "@/shared/layout/AppShellLayout.vue";
import {
  agentRouteGuard,
  legacyAgentModuleRedirect,
  legacyAgentRootRedirect,
  legacyAgentSlugModuleRedirect,
  legacyFsmCanvasRedirect,
} from "@/router/guards";
import { RouteNames } from "@/router/paths";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: AppShellLayout,
      children: [
        {
          path: "",
          redirect: "/agents",
        },
        {
          path: "agents",
          name: RouteNames.agents,
          component: AgentsListView,
        },
        {
          path: "runtime",
          name: RouteNames.globalRuntime,
          component: GlobalRuntimeView,
        },
        {
          path: "tools",
          name: RouteNames.toolsLibrary,
          component: ToolLibraryView,
        },
      ],
    },
    {
      path: "/applications",
      redirect: "/agents",
    },
    {
      path: "/applications/:legacyAgentId/modules/:moduleSlug",
      redirect: legacyAgentModuleRedirect,
    },
    {
      path: "/applications/:legacyAgentId/fsm/canvases/:canvasId",
      redirect: legacyFsmCanvasRedirect,
    },
    {
      path: "/:agentSlug/modules/:moduleSlug",
      redirect: legacyAgentSlugModuleRedirect,
    },
    {
      path: "/:agentSlug/fsm/canvases/:canvasId",
      redirect: legacyFsmCanvasRedirect,
    },
    {
      path: "/:agentSlug",
      component: AgentWorkspaceView,
      props: true,
      children: [
        {
          path: "",
          redirect: legacyAgentRootRedirect,
        },
        {
          path: "overview",
          name: RouteNames.agentOverview,
          component: AgentOverviewView,
          props: true,
        },
        {
          path: "skills",
          component: SkillsSectionLayout,
          children: [
            {
              path: "",
              name: RouteNames.agentSkills,
              component: SkillsListView,
              props: true,
            },
            {
              path: ":skillId",
              name: RouteNames.skillCanvas,
              component: SkillCanvasEditorView,
              props: true,
            },
          ],
        },
        {
          path: "actions",
          name: RouteNames.agentActions,
          component: ActionsListView,
          props: true,
        },
        {
          path: "tools",
          name: RouteNames.agentTools,
          component: ToolsListView,
          props: true,
        },
        {
          path: "tools/:instanceId",
          name: RouteNames.agentToolInstance,
          component: ToolInstanceEditorView,
          props: true,
        },
        {
          path: "logs",
          name: RouteNames.agentLogs,
          component: ToolLogsView,
          props: true,
        },
        {
          path: "runtime",
          name: RouteNames.agentRuntime,
          component: AgentRuntimeView,
          props: true,
        },
        {
          path: "runtime/simulate",
          name: RouteNames.agentRuntimeSimulate,
          component: RuntimeSimulateView,
          props: true,
        },
        {
          path: "runtime/runs/:runId",
          name: RouteNames.skillRunDetail,
          component: SkillRunDetailView,
          props: true,
        },
        {
          path: "run",
          redirect: (to) => `/${String(to.params.agentSlug)}/runtime/simulate`,
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/agents",
    },
  ],
});

router.beforeEach(agentRouteGuard);

export default router;
