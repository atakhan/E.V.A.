from definition.agent_protocol import NO_ANSWER, NO_REPLY, UNKNOWN, judge
from tools.project.protocol import prepare_delivery
from tools.project.tool import ProjectChannelTool


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
        self.delivered: list[tuple[str, str, dict]] = []

    def project_of(self, agent_slug: str) -> str | None:
        return "pochta" if agent_slug == "runtime" else None

    def runtime_agent(self, project_slug: str) -> str | None:
        return "dev-runtime" if project_slug == "dev" else "runtime"

    def hosts(self, project_slug: str, agent_slug: str) -> bool:
        return agent_slug in {"runtime", "dev-runtime", "razrabotchik"}

    def published_skills(self, agent_slug: str) -> list[dict] | None:
        if agent_slug == "dev-runtime":
            return [_listening("triage", "описание падения", True)]
        return [_listening("notice", "уведомление", False)]

    def deliver(self, agent_slug: str, skill_id: str, payload: dict) -> None:
        self.delivered.append((agent_slug, skill_id, payload))


def test_waiting_is_refused_when_the_skill_does_not_answer():
    decision = judge([_listening("notice", "уведомление", False)], "уведомление", True)
    assert decision.deliver is False
    assert decision.reason == NO_ANSWER


def test_unknown_matter_is_refused():
    decision = judge([_listening("triage", "описание падения", True)], "черновик", False)
    assert decision.reason == UNKNOWN


def test_send_delivers_when_the_skill_answers():
    directory = _Directory()
    tool = ProjectChannelTool(agent_slug="runtime", connectors=["dev"], directory=directory)
    result = tool.handle(
        "send_message",
        {"project": "dev", "matter": "описание падения", "text": "упал вход", "waits": True},
        {"vars": {}},
    )
    assert result.data["delivered"] is True
    assert directory.delivered[0][0] == "dev-runtime"
    assert directory.delivered[0][1] == "triage"
    assert directory.delivered[0][2]["reply_allowed"] is True


def test_reply_is_refused_when_nobody_is_waiting():
    directory = _Directory()
    outcome = prepare_delivery(
        directory,
        sender_agent="runtime",
        connectors=["dev"],
        target_project="dev",
        target_agent_slug="",
        matter="описание падения",
        waits=False,
        reply=True,
        reply_allowed=False,
    )
    assert outcome == NO_REPLY
