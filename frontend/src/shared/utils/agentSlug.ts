export const RESERVED_AGENT_SLUGS = [
  "agents",
  "applications",
  "api",
  "health",
  "overview",
  "skills",
  "actions",
  "tools",
] as const;

const AGENT_SLUG_PATTERN = /^[a-z][a-z0-9-]*$/;

export function normalizeAgentSlug(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

export function isValidAgentSlug(slug: string): boolean {
  return (
    slug.length >= 2 &&
    AGENT_SLUG_PATTERN.test(slug) &&
    !RESERVED_AGENT_SLUGS.includes(slug as (typeof RESERVED_AGENT_SLUGS)[number])
  );
}

export function validateAgentSlug(
  slug: string,
  isAvailable: (candidate: string) => boolean,
): string | null {
  const normalized = normalizeAgentSlug(slug);

  if (!normalized) {
    return "Укажите имя агента для URI";
  }

  if (!isValidAgentSlug(normalized)) {
    return "URI: латиница, цифры и дефис; начинается с буквы; минимум 2 символа";
  }

  if (!isAvailable(normalized)) {
    return "Такое имя агента уже занято";
  }

  return null;
}

export function suggestUniqueAgentSlug(
  base: string,
  isAvailable: (candidate: string) => boolean,
): string {
  const root = normalizeAgentSlug(base);
  const seed = root && /^[a-z]/.test(root) ? root : "agent";

  let candidate = seed;
  let suffix = 2;

  while (!isAvailable(candidate) || !isValidAgentSlug(candidate)) {
    candidate = `${seed}-${suffix}`;
    suffix += 1;
  }

  return candidate;
}

export function agentUriPreview(slug: string, suffix = "overview"): string {
  const normalized = normalizeAgentSlug(slug) || "agent-name";
  return `/${normalized}/${suffix}`;
}
