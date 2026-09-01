import { RouteNames, agentsPath, globalRuntimePath, toolsLibraryPath } from "@/router/paths";
import type { RouteLocationNormalizedLoaded } from "vue-router";

export type AppNavItem = {
  id: "agents" | "runtime" | "tools";
  label: string;
  to: string;
  routeName: string;
};

export const appNavItems: AppNavItem[] = [
  {
    id: "agents",
    label: "Agents",
    to: agentsPath(),
    routeName: RouteNames.agents,
  },
  {
    id: "runtime",
    label: "Runtime",
    to: globalRuntimePath(),
    routeName: RouteNames.globalRuntime,
  },
  {
    id: "tools",
    label: "Tools lib",
    to: toolsLibraryPath(),
    routeName: RouteNames.toolsLibrary,
  },
];

const agentWorkspaceRouteNames = new Set<string>([
  RouteNames.agentOverview,
  RouteNames.agentSkills,
  RouteNames.agentActions,
  RouteNames.agentTools,
  RouteNames.agentToolInstance,
  RouteNames.agentLogs,
  RouteNames.agentRuntime,
  RouteNames.agentRuntimeSimulate,
  RouteNames.skillRunDetail,
  RouteNames.skillCanvas,
]);

const runtimeRouteNames = new Set<string>([
  RouteNames.globalRuntime,
  RouteNames.agentRuntime,
  RouteNames.agentRuntimeSimulate,
  RouteNames.skillRunDetail,
]);

export function isAppNavActive(item: AppNavItem, route: RouteLocationNormalizedLoaded): boolean {
  const routeName = String(route.name ?? "");

  if (item.id === "agents") {
    return routeName === RouteNames.agents || agentWorkspaceRouteNames.has(routeName);
  }

  if (item.id === "runtime") {
    return runtimeRouteNames.has(routeName);
  }

  return routeName === item.routeName;
}
