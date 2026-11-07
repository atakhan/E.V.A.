/**
 * Keeps a nested desk mounted after the router has already cleared its slug.
 * `route` — follow the live URL; `leave` — freeze slugs for the exit animation.
 */
export type LeaveHold<T extends Record<string, unknown>> =
  | ({ source: "route" } & T)
  | ({ source: "leave" } & T);

export function holdFromRoute<T extends Record<string, unknown>>(value: T): LeaveHold<T> {
  return { source: "route", ...value };
}

export function holdForLeave<T extends Record<string, unknown>>(
  hold: LeaveHold<T> | null,
  fallback: T,
): LeaveHold<T> {
  if (!hold) return { source: "leave", ...fallback };
  const { source: _source, ...rest } = hold;
  return { source: "leave", ...(rest as T) };
}
