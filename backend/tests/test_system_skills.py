from definition.system_skills import library_agent_skills, runtime_agent_skills


def test_library_agent_does_not_include_talking_to_a_human():
    roles = [skill["systemRole"] for skill in library_agent_skills("2026-01-01T00:00:00Z")]
    assert roles == ["talk_to_agent"]


def test_runtime_agent_includes_both_system_skills():
    skills = runtime_agent_skills("2026-01-01T00:00:00Z")
    assert [skill["id"] for skill in skills] == ["talk_to_agent", "talk_to_human"]
    assert skills[0]["states"][0]["transitions"][0]["event"] == "agent.message.received"
    assert skills[1]["states"][0]["transitions"][0]["event"] == "channel.message.received"
