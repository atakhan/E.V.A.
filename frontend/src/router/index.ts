import { createRouter, createWebHistory } from "vue-router";
import ApplicationsListView from "@/features/applications/views/ApplicationsListView.vue";
import FsmCanvasEditorView from "@/features/modules/fsm/views/FsmCanvasEditorView.vue";
import ApplicationWorkspaceView from "@/features/workspace/views/ApplicationWorkspaceView.vue";
import {
  applicationRouteGuard,
  legacyApplicationRedirect,
  legacyFsmCanvasRedirect,
} from "@/router/guards";
import {
  applicationModulePath,
  defaultModuleSlug,
  RouteNames,
} from "@/router/paths";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/applications",
    },
    {
      path: "/applications",
      name: RouteNames.applications,
      component: ApplicationsListView,
    },
    {
      path: "/applications/:legacyAppId/modules/:moduleSlug",
      redirect: legacyApplicationRedirect,
    },
    {
      path: "/applications/:legacyAppId/fsm/canvases/:canvasId",
      redirect: legacyFsmCanvasRedirect,
    },
    {
      path: "/:appSlug",
      redirect: (to) => applicationModulePath(String(to.params.appSlug), defaultModuleSlug),
    },
    {
      path: "/:appSlug/modules/:moduleSlug",
      name: RouteNames.applicationModule,
      component: ApplicationWorkspaceView,
      props: true,
    },
    {
      path: "/:appSlug/fsm/canvases/:canvasId",
      name: RouteNames.fsmCanvas,
      component: FsmCanvasEditorView,
      props: true,
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/applications",
    },
  ],
});

router.beforeEach(applicationRouteGuard);

export default router;
