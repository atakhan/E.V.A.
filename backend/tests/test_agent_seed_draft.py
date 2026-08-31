import pytest

from definition.services.agent_service import AgentService, seed_supplier_agent
from infrastructure.db.session import session_scope


@pytest.mark.integration
def test_seed_supplier_preserves_custom_draft_layout():
    with session_scope() as session:
        service = AgentService(session)
        if service.get_agent_by_slug("supplier") is None:
            service.create_agent(name="AI Supplier Agent", slug="supplier", description="test")

        custom = {
            "name": "AI Supplier Agent",
            "description": "custom",
            "skills": [
                {
                    "id": "chat_custom",
                    "name": "Custom chat",
                    "version": "1.0.0",
                    "initial": "READY",
                    "params": [],
                    "states": [
                        {
                            "id": "READY",
                            "onEnter": [],
                            "final": False,
                            "transitions": [],
                            "x": 120,
                            "y": 240,
                            "width": 160,
                            "height": 80,
                        }
                    ],
                    "viewport": {"panX": 10, "panY": 20, "zoom": 1.25},
                }
            ],
            "actions": [],
            "tools": [],
        }
        service.upsert_draft("supplier", custom)
        session.commit()

        seed_supplier_agent(session)
        session.commit()

        loaded = service.get_agent_by_slug("supplier")
        assert loaded is not None
        assert loaded["skills"][0]["id"] == "chat_custom"
        assert loaded["skills"][0]["states"][0]["x"] == 120
        assert loaded["skills"][0]["viewport"]["zoom"] == 1.25
