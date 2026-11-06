"""Agent ↔ agent interaction manifesto — durable part of agent memory.

Channel = world tool `agents` (commands). Addresses / peers = who may exchange
with this agent, subject to allowInbound / allowOutbound. Protocols live on the
tool; the manifesto is the agent's own connect policy.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

AGENTS_TOOL_ID = "agents"
MANIFEST_VERSION = 1


def empty_interaction_manifest() -> dict[str, Any]:
    return {
        "version": MANIFEST_VERSION,
        "defaultAllowInbound": False,
        "defaultAllowOutbound": False,
        "peers": [],
    }


def empty_agent_memory() -> dict[str, Any]:
    return {"interaction": empty_interaction_manifest()}


def _flag(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _normalize_peer(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    slug = str(raw.get("agentSlug") or raw.get("agent_slug") or "").strip()
    if not slug:
        return None
    name = str(raw.get("name") or "").strip()
    peer: dict[str, Any] = {
        "agentSlug": slug,
        "allowInbound": _flag(raw.get("allowInbound", raw.get("allow_inbound")), True),
        "allowOutbound": _flag(raw.get("allowOutbound", raw.get("allow_outbound")), True),
    }
    if name:
        peer["name"] = name
    return peer


def normalize_interaction_manifest(raw: Any) -> dict[str, Any]:
    base = empty_interaction_manifest()
    if not isinstance(raw, dict):
        return base
    peers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw.get("peers") or []:
        peer = _normalize_peer(item)
        if peer is None or peer["agentSlug"] in seen:
            continue
        seen.add(peer["agentSlug"])
        peers.append(peer)
    return {
        "version": int(raw.get("version") or MANIFEST_VERSION),
        "defaultAllowInbound": _flag(raw.get("defaultAllowInbound"), False),
        "defaultAllowOutbound": _flag(raw.get("defaultAllowOutbound"), False),
        "peers": peers,
    }


def normalize_agent_memory(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return empty_agent_memory()
    return {
        "interaction": normalize_interaction_manifest(raw.get("interaction")),
    }


def agents_channel_instance() -> dict[str, Any]:
    return {
        "id": AGENTS_TOOL_ID,
        "toolId": AGENTS_TOOL_ID,
        "name": "Агенты",
        "enabled": True,
        "config": {},
    }


def ensure_agents_channel(body: dict[str, Any]) -> dict[str, Any]:
    """Guarantee the Agents world tool and an interaction manifesto on the draft."""
    tools = [item for item in (body.get("tools") or []) if isinstance(item, dict)]
    if not any(item.get("toolId") == AGENTS_TOOL_ID for item in tools):
        tools.append(agents_channel_instance())
    body["tools"] = tools
    memory = normalize_agent_memory(body.get("memory"))
    body["memory"] = memory
    return body


def _peer_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(peer["agentSlug"]): peer
        for peer in manifest.get("peers") or []
        if isinstance(peer, dict) and peer.get("agentSlug")
    }


def allow_outbound(manifest: dict[str, Any], target_slug: str) -> bool:
    slug = target_slug.strip()
    if not slug:
        return False
    peer = _peer_index(manifest).get(slug)
    if peer is not None:
        return bool(peer.get("allowOutbound"))
    return bool(manifest.get("defaultAllowOutbound"))


def allow_inbound(manifest: dict[str, Any], sender_slug: str) -> bool:
    slug = sender_slug.strip()
    if not slug:
        return False
    peer = _peer_index(manifest).get(slug)
    if peer is not None:
        return bool(peer.get("allowInbound"))
    return bool(manifest.get("defaultAllowInbound"))


def _address_id(agent_slug: str) -> str:
    return f"agents-{agent_slug}"


def _agents_addresses(world: Any) -> list[dict[str, Any]]:
    if not isinstance(world, dict):
        return []
    out: list[dict[str, Any]] = []
    for item in world.get("addresses") or []:
        if isinstance(item, dict) and item.get("toolId") == AGENTS_TOOL_ID:
            out.append(item)
    return out


def reconcile_interaction_memory(
    body: dict[str, Any],
    *,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Keep memory.interaction and world addresses for `agents` in sync.

    Addresses on the Agents channel are the spatial peers; the manifesto holds
    connect flags and defaults (and is what memory / delivery read).
    """
    prev_body = previous if isinstance(previous, dict) else {}
    prev_manifest = normalize_interaction_manifest(
        (prev_body.get("memory") or {}).get("interaction")
        if isinstance(prev_body.get("memory"), dict)
        else None
    )
    payload_manifest = normalize_interaction_manifest(
        (body.get("memory") or {}).get("interaction")
        if isinstance(body.get("memory"), dict)
        else None
    )
    prev_peers = _peer_index(prev_manifest)
    payload_peers = _peer_index(payload_manifest)

    world = body.get("world") if isinstance(body.get("world"), dict) else {"addresses": []}
    other_addresses = [
        item
        for item in (world.get("addresses") or [])
        if isinstance(item, dict) and item.get("toolId") != AGENTS_TOOL_ID
    ]
    address_peers: dict[str, dict[str, Any]] = {}
    for address in _agents_addresses(world):
        slug = str((address.get("config") or {}).get("agentSlug") or "").strip()
        if not slug:
            continue
        address_peers[slug] = address

    # Peers from manifesto payload that are not yet addresses still count.
    peer_slugs = list(dict.fromkeys([*address_peers.keys(), *payload_peers.keys()]))

    peers: list[dict[str, Any]] = []
    agent_addresses: list[dict[str, Any]] = []
    for slug in peer_slugs:
        prior = payload_peers.get(slug) or prev_peers.get(slug) or {}
        address = address_peers.get(slug) or {}
        name = str(
            prior.get("name")
            or address.get("name")
            or slug
        ).strip()
        peer = {
            "agentSlug": slug,
            "allowInbound": _flag(prior.get("allowInbound"), True),
            "allowOutbound": _flag(prior.get("allowOutbound"), True),
            "name": name,
        }
        peers.append(peer)
        config = dict(address.get("config") or {})
        config["agentSlug"] = slug
        agent_addresses.append(
            {
                "id": str(address.get("id") or _address_id(slug)),
                "toolId": AGENTS_TOOL_ID,
                "name": name,
                "config": config,
                **(
                    {"credentialId": address["credentialId"]}
                    if isinstance(address.get("credentialId"), str) and address.get("credentialId")
                    else {}
                ),
            }
        )

    body["memory"] = {
        "interaction": {
            "version": MANIFEST_VERSION,
            "defaultAllowInbound": _flag(
                payload_manifest.get("defaultAllowInbound"),
                bool(prev_manifest.get("defaultAllowInbound")),
            ),
            "defaultAllowOutbound": _flag(
                payload_manifest.get("defaultAllowOutbound"),
                bool(prev_manifest.get("defaultAllowOutbound")),
            ),
            "peers": peers,
        }
    }
    body["world"] = {**world, "addresses": [*other_addresses, *agent_addresses]}
    return body


def link_agent_peer(
    body: dict[str, Any],
    peer_slug: str,
    *,
    name: str = "",
    allow_inbound: bool = True,
    allow_outbound: bool = True,
) -> dict[str, Any]:
    """Add or refresh a peer on this agent's Agents channel + manifesto."""
    slug = peer_slug.strip()
    if not slug:
        return body
    ensure_agents_channel(body)
    memory = normalize_agent_memory(body.get("memory"))
    manifest = memory["interaction"]
    peers = [peer for peer in manifest["peers"] if peer.get("agentSlug") != slug]
    peers.append(
        {
            "agentSlug": slug,
            "allowInbound": allow_inbound,
            "allowOutbound": allow_outbound,
            **({"name": name.strip()} if name.strip() else {"name": slug}),
        }
    )
    manifest["peers"] = peers
    body["memory"] = memory

    world = body.get("world") if isinstance(body.get("world"), dict) else {"addresses": []}
    addresses = [item for item in (world.get("addresses") or []) if isinstance(item, dict)]
    rest = [
        item
        for item in addresses
        if not (
            item.get("toolId") == AGENTS_TOOL_ID
            and str((item.get("config") or {}).get("agentSlug") or "").strip() == slug
        )
    ]
    label = name.strip() or slug
    rest.append(
        {
            "id": _address_id(slug),
            "toolId": AGENTS_TOOL_ID,
            "name": label,
            "config": {"agentSlug": slug},
        }
    )
    body["world"] = {**world, "addresses": rest}
    return body


def new_address_id() -> str:
    return f"addr_{uuid4().hex[:10]}"
