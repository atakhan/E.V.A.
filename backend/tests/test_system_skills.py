from definition.system_skills import (
    ensure_life_skill_in_body,
    library_agent_skills,
    runtime_agent_skills,
)


def test_library_agent_does_not_include_talking_to_a_human():
    roles = [skill["systemRole"] for skill in library_agent_skills("2026-01-01T00:00:00Z")]
    assert roles == ["talk_to_agent", "life"]


def test_runtime_agent_includes_system_skills_and_alive_life():
    skills = runtime_agent_skills("2026-01-01T00:00:00Z")
    assert [skill["id"] for skill in skills] == ["talk_to_agent", "talk_to_human", "life"]
    assert skills[0]["states"][0]["transitions"][0]["event"] == "agent.message.received"
    assert skills[1]["states"][0]["transitions"][0]["event"] == "channel.message.received"
    life = skills[2]
    assert life["name"] == "Жизнь"
    assert life["initial"] == "alive"
    assert life["states"][0]["id"] == "alive"
    assert life["states"][0]["final"] is False
    assert life["states"][0]["transitions"][0]["event"] == "life.started"
    assert life["params"] == []
    # Life must not listen on channel ingress.
    assert all(t["event"] != "channel.message.received" for t in life["states"][0]["transitions"])


def test_ensure_life_skill_in_body_is_idempotent():
    body: dict = {"skills": [{"id": "talk_to_agent", "systemRole": "talk_to_agent"}]}
    assert ensure_life_skill_in_body(body, now="2026-01-01T00:00:00Z") is True
    assert [skill["id"] for skill in body["skills"]] == ["talk_to_agent", "life"]
    assert ensure_life_skill_in_body(body, now="2026-01-02T00:00:00Z") is False
    assert [skill["id"] for skill in body["skills"]] == ["talk_to_agent", "life"]
