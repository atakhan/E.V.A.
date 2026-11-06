from definition.agent_protocol import NO_ANSWER
from tools.agents.protocol import NO_PEER, prepare_agent_delivery
from tools.agents.tool import AgentsChannelTool


def _listening(skill_id: str, accepts: str, answers: bool) -> dict:
    return {
        "id": skill_id,
        "accepts": accepts,
        "answers": answers,
        "initial": "listening",
        "states": [
            {
                "id": "listening",
                "transitions": [{"event": "agent.message.received", "to": "listening"}],
            }
        ],
    }


class _Directory:
    def __init__(self) -> None:
        self.delivered: list[tuple[str, str, dict, str]] = []
        self.manifests = {
            "eva": {
                "peers": [
                    {"agentSlug": "rt-dev", "allowInbound": True, "allowOutbound": True},
                ]
            },
            "rt-dev": {
                "peers": [
                    {"agentSlug": "eva", "allowInbound": True, "allowOutbound": True},
                ]
            },
        }

    def agent_exists(self, agent_slug: str) -> bool:
        return agent_slug in {"eva", "rt-dev"}

    def interaction_manifest(self, agent_slug: str) -> dict:
        return self.manifests.get(agent_slug, {})

    def published_skills(self, agent_slug: str) -> list[dict] | None:
        if agent_slug == "rt-dev":
            return [_listening("triage", "описание падения", True)]
        return [_listening("notice", "уведомление", False)]

    def deliver(self, agent_slug: str, skill_id: str, payload: dict, *, source: str = "agents") -> None:
        self.delivered.append((agent_slug, skill_id, payload, source))


def test_agents_send_delivers_when_peer_linked():
    directory = _Directory()
    tool = AgentsChannelTool(agent_slug="eva", directory=directory)
    result = tool.handle(
        "send_message",
        {"agent": "rt-dev", "matter": "описание падения", "text": "упал вход", "waits": True},
        {"vars": {}},
    )
    assert result.data["delivered"] is True
    assert directory.delivered[0][0] == "rt-dev"
    assert directory.delivered[0][3] == "agents"


def test_agents_send_refused_without_peer():
    directory = _Directory()
    directory.manifests["eva"] = {"peers": []}
    outcome = prepare_agent_delivery(
        directory,
        sender_agent="eva",
        target_agent_slug="rt-dev",
        matter="описание падения",
        waits=False,
        reply=False,
        reply_allowed=False,
    )
    assert outcome == NO_PEER


def test_waiting_refused_when_skill_does_not_answer():
    directory = _Directory()
    directory.manifests["eva"]["peers"] = [
        {"agentSlug": "rt-dev", "allowInbound": True, "allowOutbound": True},
    ]
    # Force a non-answering skill match by changing target skills via matter on eva→ notice
    directory.published_skills = lambda agent_slug: [_listening("notice", "уведомление", False)]  # type: ignore[method-assign]
    outcome = prepare_agent_delivery(
        directory,
        sender_agent="eva",
        target_agent_slug="rt-dev",
        matter="уведомление",
        waits=True,
        reply=False,
        reply_allowed=False,
    )
    assert outcome == NO_ANSWER
