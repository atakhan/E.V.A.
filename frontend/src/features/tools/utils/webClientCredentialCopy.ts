/** Подписи и соответствие секретов Web Client (E.V.A. credential ↔ .env бэкенда). */
export const WEB_CLIENT_CREDENTIAL_COPY = {
  outbound: {
    direction: "E.V.A. → ваш бэкенд",
    fieldLabel: "Ключ E.V.A. → ваш бэкенд",
    fieldHint: "E.V.A. отправляет в Authorization при вызове /eva/health, /eva/messages…",
    backendEnvVar: "EVA_OUTBOUND_KEY",
    backendEnvAlt: "WEB_CLIENT_OUTBOUND_KEY",
    whereOnBackend: "Проверяйте на своих эндпоинтах /eva/*",
  },
  inbound: {
    direction: "Ваш бэкенд → E.V.A.",
    fieldLabel: "Ключ вашего бэкенда → E.V.A.",
    fieldHint: "Ваш API отправляет в Authorization при POST на ingress E.V.A.",
    backendEnvVar: "EVA_INBOUND_KEY",
    backendEnvAlt: null as string | null,
    whereOnBackend: "Ingress URL и outbox E.V.A.",
  },
} as const;

export function webClientEnvSnippet(options: {
  ingressUrl: string;
  outboundKey?: string;
  inboundKey?: string;
}): string {
  const { outbound, inbound } = WEB_CLIENT_CREDENTIAL_COPY;
  const out = options.outboundKey ?? `<${outbound.fieldLabel}>`;
  const inn = options.inboundKey ?? `<${inbound.fieldLabel}>`;
  return `# ${inbound.direction}
EVA_INGRESS_URL=${options.ingressUrl}
${inbound.backendEnvVar}=${inn}

# ${outbound.direction}
${outbound.backendEnvVar}=${out}
# или ${outbound.backendEnvAlt}=${out}`;
}

export function webClientIngressUrlFallback(agentSlug: string): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    return `${window.location.origin}/api/channels/web/${agentSlug}/events`;
  }
  return `/api/channels/web/${agentSlug}/events`;
}
