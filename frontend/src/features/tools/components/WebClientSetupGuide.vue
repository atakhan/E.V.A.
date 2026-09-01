<script setup lang="ts">
import { computed } from "vue";
import type { WebClientIntegrationInfo } from "@/features/tools/services/webClientApi";
import type { WebClientBindingConfig } from "@/features/tools/utils/webClientConfig";
import { WEB_CLIENT_DEFAULTS } from "@/features/tools/utils/webClientConfig";
import {
  WEB_CLIENT_CREDENTIAL_COPY,
  webClientEnvSnippet,
} from "@/features/tools/utils/webClientCredentialCopy";

const props = defineProps<{
  agentSlug: string;
  bindingConfig: WebClientBindingConfig;
  integration?: WebClientIntegrationInfo | null;
  ingressCurl?: string;
  hasCredential?: boolean;
}>();

const paths = computed(() => ({
  health: props.bindingConfig.healthPath ?? WEB_CLIENT_DEFAULTS.healthPath,
  send: props.bindingConfig.sendMessagePath ?? WEB_CLIENT_DEFAULTS.sendMessagePath,
  snapshot: props.bindingConfig.getSnapshotPath ?? WEB_CLIENT_DEFAULTS.getSnapshotPath,
  auth: props.bindingConfig.authStyle ?? WEB_CLIENT_DEFAULTS.authStyle,
}));

const ingressUrl = computed(
  () =>
    props.integration?.ingressUrl ??
    `/api/channels/web/${props.agentSlug}/events`,
);

const outboxUrl = computed(
  () =>
    props.integration?.outboxUrlTemplate?.replace("{sessionId}", "<sessionId>") ??
    `/api/channels/web/${props.agentSlug}/sessions/<sessionId>/outbox`,
);

const authHeader = computed(() =>
  paths.value.auth === "x-api-key"
    ? "X-Api-Key: <OUTBOUND_API_KEY>"
    : "Authorization: Bearer <OUTBOUND_API_KEY>",
);

const outboundExample = computed(
  () => `POST ${paths.value.send}
${authHeader.value}
Content-Type: application/json

{
  "sessionId": "web:demo:1",
  "text": "Ответ агента для UI",
  "meta": { "source": "eva" }
}`,
);

const snapshotExample = computed(
  () => `GET ${paths.value.snapshot}?sessionId=web:demo:1
${authHeader.value}`,
);

const envExample = computed(() =>
  webClientEnvSnippet({
    ingressUrl: ingressUrl.value,
  }),
);

const credentialCopy = WEB_CLIENT_CREDENTIAL_COPY;

const inboundPayloadExample = `{
  "sessionId": "web:demo:1",
  "type": "channel.message.received",
  "skillId": "my_skill",
  "payload": {
    "text": "Сообщение пользователя",
    "context": { "page": "/requests", "requestId": "42" }
  }
}`;
</script>

<template>
  <section class="rounded-xl border border-primary/25 bg-primary/5">
    <div class="collapse collapse-arrow">
      <input type="checkbox" checked />
      <div class="collapse-title min-h-0 py-3 text-sm font-semibold">
        Как подключить Web Client к агенту
      </div>
      <div class="collapse-content space-y-4 pb-4 text-sm leading-relaxed text-base-content/80">
        <p>
          <strong>Web Client</strong> связывает агента E.V.A. с бэкендом вашего веб-приложения в
          двух направлениях. Агент получает события от UI и отвечает через команды
          <code class="rounded bg-base-200 px-1 font-mono text-xs">web_client.send_message</code>
          и
          <code class="rounded bg-base-200 px-1 font-mono text-xs">web_client.get_snapshot</code>.
        </p>

        <div class="overflow-x-auto rounded-lg border border-base-300 bg-base-100">
          <table class="table table-xs">
            <thead>
              <tr>
                <th>Направление</th>
                <th>Поле в credential E.V.A.</th>
                <th>Переменная в .env бэкенда</th>
              </tr>
            </thead>
            <tbody class="text-xs">
              <tr>
                <td>{{ credentialCopy.outbound.direction }}</td>
                <td class="font-medium">{{ credentialCopy.outbound.fieldLabel }}</td>
                <td class="font-mono">
                  {{ credentialCopy.outbound.backendEnvVar }}
                  <span class="font-sans text-base-content/50">
                    (или {{ credentialCopy.outbound.backendEnvAlt }})
                  </span>
                </td>
              </tr>
              <tr>
                <td>{{ credentialCopy.inbound.direction }}</td>
                <td class="font-medium">{{ credentialCopy.inbound.fieldLabel }}</td>
                <td class="font-mono">{{ credentialCopy.inbound.backendEnvVar }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="text-xs text-base-content/55">
          Inbound/outbound в API E.V.A. — с точки зрения платформы. В вашем приложении удобнее
          думать «что куда кладу в .env»: для ingress — inbound, для защиты
          <code class="font-mono">/eva/*</code> — outbound.
        </p>

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded-lg border border-base-300 bg-base-100/80 p-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
              Входящие · ваш API → E.V.A.
            </p>
            <p class="mt-1 text-xs">
              Сообщения пользователя на <strong>ingress</strong> E.V.A. Секрет —
              <strong>{{ credentialCopy.inbound.fieldLabel }}</strong>
              → <code class="font-mono">{{ credentialCopy.inbound.backendEnvVar }}</code>.
            </p>
          </div>
          <div class="rounded-lg border border-base-300 bg-base-100/80 p-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
              Исходящие · E.V.A. → ваш API
            </p>
            <p class="mt-1 text-xs">
              Runtime вызывает <strong>backend base URL</strong>. Секрет —
              <strong>{{ credentialCopy.outbound.fieldLabel }}</strong>
              → <code class="font-mono">{{ credentialCopy.outbound.backendEnvVar }}</code>.
              Проверка — Verify ниже.
            </p>
          </div>
        </div>

        <div>
          <p class="font-medium">Шаги на этой странице</p>
          <ol class="mt-2 list-decimal space-y-1.5 pl-5 text-xs">
            <li>Убедитесь, что instance <strong>Enabled</strong>.</li>
            <li>
              Создайте <strong>Credential</strong>: URL бэкенда и оба ключа (см. таблицу
              соответствия выше).
            </li>
            <li>Выберите credential в списке (привязка к instance — автоматически).</li>
            <li>Нажмите <strong>Verify</strong> — E.V.A. проверит <code class="font-mono">{{ paths.health }}</code>.</li>
            <li>
              Нажмите <strong>Скопировать .env</strong> и вставьте секреты в конфиг приложения.
            </li>
            <li>Реализуйте HTTP-контракт на бэкенде или используйте stub для теста.</li>
            <li>Опубликуйте агента в Overview и проверьте в Simulate или из UI приложения.</li>
          </ol>
        </div>

        <div class="space-y-2">
          <p class="font-medium">Контракт вашего бэкенда (исходящие вызовы E.V.A.)</p>
          <p class="text-xs text-base-content/60">
            Пути настраиваются в блоке «Пути API» ниже. По умолчанию — префикс
            <code class="font-mono">/eva/*</code> (как в
            <code class="font-mono">ai_supplier</code> и
            <code class="font-mono">examples/web_client_stub</code>).
          </p>
          <div class="overflow-x-auto rounded-lg border border-base-300 bg-base-100">
            <table class="table table-xs">
              <thead>
                <tr>
                  <th>Метод</th>
                  <th>Путь</th>
                  <th>Назначение</th>
                </tr>
              </thead>
              <tbody class="font-mono text-[11px]">
                <tr>
                  <td>GET</td>
                  <td>{{ paths.health }}</td>
                  <td class="font-sans">Health-check (Verify)</td>
                </tr>
                <tr>
                  <td>POST</td>
                  <td>{{ paths.send }}</td>
                  <td class="font-sans">Ответ агента в UI (<code>send_message</code>)</td>
                </tr>
                <tr>
                  <td>GET</td>
                  <td>{{ paths.snapshot }}?sessionId=…</td>
                  <td class="font-sans">Контекст сессии (<code>get_snapshot</code>)</td>
                </tr>
              </tbody>
            </table>
          </div>
          <details class="rounded-lg border border-base-300 bg-base-100/60">
            <summary class="cursor-pointer px-3 py-2 text-xs font-medium">Пример send_message</summary>
            <pre class="overflow-x-auto p-3 font-mono text-[11px] leading-snug">{{ outboundExample }}</pre>
          </details>
          <details class="rounded-lg border border-base-300 bg-base-100/60">
            <summary class="cursor-pointer px-3 py-2 text-xs font-medium">Пример get_snapshot</summary>
            <pre class="overflow-x-auto p-3 font-mono text-[11px] leading-snug">{{ snapshotExample }}</pre>
          </details>
        </div>

        <div class="space-y-2">
          <p class="font-medium">Ingress E.V.A. (входящие от вашего бэкенда)</p>
          <p class="text-xs text-base-content/60">
            Ваш бэкенд пересылает сообщения пользователя на ingress. Тип события обычно
            <code class="font-mono">channel.message.received</code>; для UI-событий —
            <code class="font-mono">web.state.changed</code>. Поле
            <code class="font-mono">skillId</code> опционально — иначе runtime выберет skill по
            умолчанию.
          </p>
          <div class="rounded-lg border border-base-300 bg-base-100 p-3">
            <p class="text-[11px] uppercase tracking-wide text-base-content/50">Ingress URL</p>
            <p class="mt-1 break-all font-mono text-xs">{{ ingressUrl }}</p>
            <p v-if="!hasCredential" class="mt-2 text-xs text-warning">
              Выберите credential ниже — URL подтвердится после привязки.
            </p>
          </div>
          <details class="rounded-lg border border-base-300 bg-base-100/60">
            <summary class="cursor-pointer px-3 py-2 text-xs font-medium">Тело POST ingress</summary>
            <pre class="overflow-x-auto p-3 font-mono text-[11px] leading-snug">{{ inboundPayloadExample }}</pre>
          </details>
          <details v-if="ingressCurl" class="rounded-lg border border-base-300 bg-base-100/60">
            <summary class="cursor-pointer px-3 py-2 text-xs font-medium">curl для теста</summary>
            <pre class="overflow-x-auto p-3 font-mono text-[11px] leading-snug">{{ ingressCurl }}</pre>
          </details>
        </div>

        <div class="space-y-2">
          <p class="font-medium">Outbox (опционально)</p>
          <p class="text-xs text-base-content/60">
            UI может опрашивать outbox E.V.A., если не использует прямой push от вашего бэкенда.
            Тот же секрет, что
            <strong>{{ credentialCopy.inbound.fieldLabel }}</strong>
            (<code class="font-mono">{{ credentialCopy.inbound.backendEnvVar }}</code>).
          </p>
          <p class="break-all font-mono text-xs">{{ outboxUrl }}</p>
        </div>

        <div class="space-y-2">
          <p class="font-medium">Переменные окружения в вашем приложении</p>
          <pre class="overflow-x-auto rounded-lg border border-base-300 bg-base-200/50 p-3 font-mono text-[11px] leading-snug">{{ envExample }}</pre>
        </div>

        <div class="space-y-2">
          <p class="font-medium">Локальная разработка и Docker</p>
          <ul class="list-disc space-y-1 pl-5 text-xs">
            <li>
              E.V.A. в Docker, приложение на хосте:
              <code class="font-mono">http://host.docker.internal:3000</code> в credential.
            </li>
            <li>
              Оба в Docker Compose: hostname сервиса, например
              <code class="font-mono">http://web-client-stub:8765</code> или
              <code class="font-mono">http://backend:3000</code>.
            </li>
            <li>
              Ingress с хоста в E.V.A. в Docker: публичный URL бэкенда (часто
              <code class="font-mono">http://localhost:8000</code>).
            </li>
            <li v-if="integration?.localDevHints.stubOnHost">
              Тестовый stub E.V.A.:
              <code class="font-mono">{{ integration.localDevHints.stubOnHost }}</code>
              (сервис <code class="font-mono">web-client-stub</code> в compose).
            </li>
          </ul>
        </div>

        <div class="rounded-lg border border-dashed border-base-300 bg-base-100/50 p-3 text-xs">
          <p class="font-medium">Связь с Skills и Actions</p>
          <p class="mt-1 text-base-content/65">
            В FSM skill используйте entry-event
            <code class="font-mono">channel.message.received</code> для чата. В action recipe —
            шаги <code class="font-mono">web_client.send_message</code> и
            <code class="font-mono">web_client.get_snapshot</code>. После изменений опубликуйте
            агента — runtime исполняет только опубликованную версию.
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
