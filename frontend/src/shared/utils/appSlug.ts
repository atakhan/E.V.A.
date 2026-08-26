export const RESERVED_APP_SLUGS = ["applications", "api", "health"] as const;

const APP_SLUG_PATTERN = /^[a-z][a-z0-9-]*$/;

export function normalizeAppSlug(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

export function isValidAppSlug(slug: string): boolean {
  return (
    slug.length >= 2 &&
    APP_SLUG_PATTERN.test(slug) &&
    !RESERVED_APP_SLUGS.includes(slug as (typeof RESERVED_APP_SLUGS)[number])
  );
}

export function validateAppSlug(
  slug: string,
  isAvailable: (candidate: string) => boolean,
): string | null {
  const normalized = normalizeAppSlug(slug);

  if (!normalized) {
    return "Укажите имя приложения для URI";
  }

  if (!isValidAppSlug(normalized)) {
    return "URI: латиница, цифры и дефис; начинается с буквы; минимум 2 символа";
  }

  if (!isAvailable(normalized)) {
    return "Такое имя приложения уже занято";
  }

  return null;
}

export function suggestUniqueAppSlug(
  base: string,
  isAvailable: (candidate: string) => boolean,
): string {
  const root = normalizeAppSlug(base);
  const seed = root && /^[a-z]/.test(root) ? root : "app";

  let candidate = seed;
  let suffix = 2;

  while (!isAvailable(candidate) || !isValidAppSlug(candidate)) {
    candidate = `${seed}-${suffix}`;
    suffix += 1;
  }

  return candidate;
}

export function appUriPreview(slug: string, suffix = "modules/fsm"): string {
  const normalized = normalizeAppSlug(slug) || "app-name";
  return `/${normalized}/${suffix}`;
}
