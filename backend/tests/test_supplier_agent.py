from definition.validation.validate_agent import validate_agent
from scenarios.supplier_agent_document import build_supplier_agent_document


def test_supplier_agent_document_valid():
    doc = build_supplier_agent_document()
    doc["tools"][0]["credentialId"] = "test-credential-id"
    report = validate_agent(doc)
    assert report["errors"] == 0, report
