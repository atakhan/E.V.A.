import type { WorldAddress } from "@/features/agents/types/world";

export type WorldAddressStatus = "red" | "yellow" | "green";

export interface WorldAddressEvaluation {
  status: WorldAddressStatus;
  reason: string;
}

/** Public credential fields the address light can see. Secrets stay on the server. */
export interface AddressCredentialSnapshot {
  meta?: {
    verified?: boolean;
    health_status?: number | null;
    health_error?: string | null;
  };
}

export interface EvaluateWorldAddressOptions {
  /** False while the credential list is still loading. */
  credentialsReady?: boolean;
}

const PLACE_REQUIRED: Record<string, string[]> = {
  telegram: ["chat_id"],
};

function filled(value: unknown): boolean {
  return typeof value === "string" ? value.trim().length > 0 : value != null && value !== "";
}

/**
 * Traffic light for one address (a place, or a web-client application).
 * Yellow — required fields are still empty, or the application has not been checked.
 * Red — filled, but the last connection check failed or the keys are gone.
 * Green — the address can be used.
 */
export function evaluateWorldAddress(
  address: Pick<WorldAddress, "toolId" | "credentialId" | "config">,
  credential: AddressCredentialSnapshot | null,
  options?: EvaluateWorldAddressOptions,
): WorldAddressEvaluation {
  if (address.toolId === "web_client") {
    return evaluateWebClientAddress(address, credential, options);
  }

  const required = PLACE_REQUIRED[address.toolId] ?? [];
  const missing = required.some((fieldId) => !filled(address.config?.[fieldId]));
  if (missing) {
    return { status: "yellow", reason: "Адрес не заполнен" };
  }
  return { status: "green", reason: "Адрес готов" };
}

function evaluateWebClientAddress(
  address: Pick<WorldAddress, "credentialId">,
  credential: AddressCredentialSnapshot | null,
  options?: EvaluateWorldAddressOptions,
): WorldAddressEvaluation {
  const credentialId = address.credentialId?.trim() ?? "";
  if (!credentialId) {
    return { status: "yellow", reason: "Приложение не заполнено" };
  }
  if (options?.credentialsReady === false) {
    return { status: "yellow", reason: "Проверяем приложение" };
  }
  if (!credential) {
    return { status: "red", reason: "Ключи приложения не найдены" };
  }

  const meta = credential.meta ?? {};
  const healthStatus = meta.health_status;
  const failed =
    meta.verified === false || (typeof healthStatus === "number" && healthStatus >= 400);
  if (failed) {
    const statusText = typeof healthStatus === "number" ? `: HTTP ${healthStatus}` : "";
    return { status: "red", reason: `Проверка связи не прошла${statusText}` };
  }
  if (meta.verified === true) {
    return { status: "green", reason: "Приложение готово" };
  }
  return { status: "yellow", reason: "Связь ещё не проверена" };
}
