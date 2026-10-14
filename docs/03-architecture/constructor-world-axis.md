# Constructor world axis

**Status:** v0.1 architecture note, aligned with the constructor canvas  
**Related concept:** addresses → channels (каналы) → agent → skills  
**Concept (not a contract):** [`../01-concept/spatial-model.md`](../01-concept/spatial-model.md)

## Purpose

The agent constructor canvas is a **docking table**.

Left to right:

1. **Addresses** — concrete places hanging on a channel
2. **Channels (каналы)** — world-facing tool types the agent has turned on
3. **Agent** — hub body (circle, card, then details)
4. **Skills** — repertoire on the right, plus «Добавить навык»

Internal tools (`llm`, `text`, `polza_ai_llm`, …) are not on this axis. They stay in the tool library under «Инструменты действий» and inside action steps.

World channels today: `telegram`, `web_client` (`world: true` on the catalog manifest).

## How a channel gets onto the table

Idle channels are not drawn. The column shows only connected channels and an **Добавить** button under them.

«Добавить» opens a full-screen sheet of every world tool in the E.V.A. catalog. Picking one enables the singleton `ToolInstance` for that `toolId` and draws the cable. The settings panel does not open by itself.

The same panel opens later from a click on the cable or on the channel block. Removing a channel, an address, or a skill asks for confirmation first.

Side panels (channel, address, skill) are full height, flush to the right edge.

## What a channel is, in the product and in the code

The UI word is **канал**. Code and layout names still say kind (`worldKinds`, `connectKind`, `KindConnectorPanel`).

| Phenomenon | Entity |
|------------|--------|
| Channel | Catalog tool with `world: true` |
| Cable | One enabled `ToolInstance` of that `toolId` |
| Address | `agent.world.addresses[]` (`id`, `toolId`, `name`, optional `credentialId`, `config`) |
| Cable color | Derived by `evaluateWorldLink`. Not stored |

At most one enabled instance per world `toolId`. Disconnect sets `enabled: false` and keeps credentials and addresses.

## Cable color

- **off** — channel is not on the table
- **red** — the channel itself cannot work. Telegram with no bot token on the instance and no address credential
- **yellow** — unfinished. Web Client has no address with a credential («Нет подключённого приложения»), or no skill listens to the channel's events and no action calls it
- **green** — the channel can work and a behavior path exists

For Web Client, a credential left on the channel instance does **not** count. Only an address with `credentialId` does. A skill that listens to `channel.message.received` still counts as a behavior path (that event id is shared with Telegram).

Yellow does not create a skill.

## Address color

The line from an address to its channel, and the address card, use the same three colors. Derived by `evaluateWorldAddress`. Not stored on the address.

- **yellow** — not filled yet. A web client application has no credential, or the credential exists but the connection has not been checked. A Telegram address has no `chat_id`
- **red** — filled, but not usable. The last web client health check failed (for example HTTP 404), or the address points at a credential that no longer exists
- **green** — usable. The web client check returned success, or the Telegram chat id is set

A failed check is written onto the credential (`verified: false`, `health_status`) before the verify request returns an error, so the address stays red after the panel closes. The channel cable does not change color because one application failed.

## What is configured where

**Telegram**

- Channel panel: bot token (credential) and instance `config`
- Address: a chat (`config.chat_id`). The panel can store an optional address credential. The cable treats that credential as a token. Publish validation still requires `credentialId` on the Telegram instance, and outbound calls use the instance credential

**Web Client**

- Channel panel: shared HTTP contract only (`healthPath`, `sendMessagePath`, `getSnapshotPath`, `authStyle`, `timeoutSec`). No URL and no keys
- Address: one application. Name, base URL, the key E.V.A. uses to call the app, the key the app uses to call E.V.A. Those secrets are a `web_client` credential referenced by `address.credentialId`
- A session is not an address. It appears when a person opens the app

Several applications are several addresses on the one Web Client channel (for example СОУС and supplier service).

## Runtime consequence

Ingress `POST /api/channels/web/{slug}/events` matches `inbound_api_key` to a credential, then to the address that holds that `credentialId`. The event payload gains `web_client_credential_id` and, when the address is found, `web_client_address_id`. Those keys land in run `vars`.

`send_message` and `get_snapshot` build the HTTP client from `vars.web_client_credential_id` when it is set. Otherwise they use the credential on the channel instance, if any. Paths and auth style still come from the instance `config`.

The registry still builds when the Web Client instance has no credential of its own, so an address-only setup does not fail tool assembly. A call with neither an address credential in `vars` nor an instance credential returns `web_client application is not configured`.

Server validation `missing_credential` is skipped for an enabled `web_client` instance when some address of that `toolId` has `credentialId`. Telegram and Polza still require `credentialId` on the instance itself.

## Code pointers

- Manifests: `backend/tools/telegram/manifest.py`, `backend/tools/web_client/manifest.py`
- Agent world schema: `backend/definition/schemas/agent_api.py` (`AgentWorldApi`, `WorldAddressApi`)
- Ingress: `backend/app/api/channels/web.py`
- Outbound choice: `backend/tools/web_client/tool.py` (`_http_for`), assembly in `backend/runtime/definition_loader.py`
- FE types: `frontend/src/features/agents/types/world.ts`
- Link status: `frontend/src/features/agents/utils/evaluateWorldLink.ts`
- Connect / addresses: `frontend/src/features/agents/composables/useWorldConnections.ts`
- Canvas: `frontend/src/features/constructor/components/InfiniteCanvas.vue`
- Catalog sheet: `frontend/src/features/constructor/components/WorldKindCatalogSheet.vue`
- Channel panel: `frontend/src/features/constructor/components/KindConnectorPanel.vue`
- Address panel: `frontend/src/features/constructor/components/AddressConfigPanel.vue`
- Global library grouping: `frontend/src/features/tools/views/ToolLibraryView.vue`
