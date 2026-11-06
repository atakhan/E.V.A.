from definition.interaction_manifest import (
    allow_inbound,
    allow_outbound,
    empty_interaction_manifest,
    link_agent_peer,
    normalize_interaction_manifest,
    reconcile_interaction_memory,
)


def test_defaults_deny_unknown_peers():
    manifest = empty_interaction_manifest()
    assert allow_outbound(manifest, "rt-a") is False
    assert allow_inbound(manifest, "eva") is False


def test_peer_flags_override_defaults():
    manifest = normalize_interaction_manifest(
        {
            "defaultAllowInbound": False,
            "defaultAllowOutbound": False,
            "peers": [
                {"agentSlug": "rt-a", "allowInbound": True, "allowOutbound": False},
            ],
        }
    )
    assert allow_inbound(manifest, "rt-a") is True
    assert allow_outbound(manifest, "rt-a") is False


def test_link_agent_peer_writes_address_and_manifest():
    body: dict = {"tools": [], "world": {"addresses": []}, "memory": {}}
    link_agent_peer(body, "rt-mail", name="Почта")
    peers = body["memory"]["interaction"]["peers"]
    assert peers[0]["agentSlug"] == "rt-mail"
    assert any(
        item.get("toolId") == "agents" and item.get("config", {}).get("agentSlug") == "rt-mail"
        for item in body["world"]["addresses"]
    )
    assert any(item.get("toolId") == "agents" for item in body["tools"])


def test_reconcile_keeps_allow_flags_from_previous():
    previous = {
        "memory": {
            "interaction": {
                "peers": [{"agentSlug": "rt-a", "allowInbound": False, "allowOutbound": True}],
            }
        }
    }
    body = {
        "world": {
            "addresses": [
                {"id": "agents-rt-a", "toolId": "agents", "name": "A", "config": {"agentSlug": "rt-a"}},
            ]
        },
        "memory": {},
    }
    reconcile_interaction_memory(body, previous=previous)
    peer = body["memory"]["interaction"]["peers"][0]
    assert peer["allowInbound"] is False
    assert peer["allowOutbound"] is True
