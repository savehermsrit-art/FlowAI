from app.research import ResearchIndex, load_corpus
from app.rules import minimal_evidence_set
from app.db import DB, Evaluation, Profile, Proposal
from app.monitor import proposal_impact
from sqlalchemy import select
from conftest import login


def test_archived_sources_and_citations_resolve():
    sources, passages, schemes = load_corpus()
    assert len(sources) == 11
    assert all(s["status"] == "fetched" for s in sources.values())
    assert len(schemes) == 3
    lookup = {p["id"]: p for p in passages}
    answer = ResearchIndex().answer("What is the age requirement for Sandhya Suraksha?")
    assert answer["status"] == "source_linked_research_annotation"
    assert "65" in answer["answer"]
    assert all(c["id"] in lookup and c["url"] == lookup[c["id"]]["url"] for c in answer["citations"])


def test_research_abstains_on_unsupported_question(client):
    response = client.get("/api/v1/research/ask?q=What%20is%20the%20weather%20tomorrow%3F")
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["citations"] == []


def test_kannada_research_answer_has_official_passage(client):
    response = client.get("/api/v1/research/ask", params={"q": "ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಯೋಜನೆಗೆ ಆದಾಯ ಮಿತಿ ಎಷ್ಟು?"})
    assert response.status_code == 200
    result = response.json()
    assert result["citations"] and "32,000" in result["answer"]
    assert "dssp.karnataka.gov.in" in result["citations"][0]["url"]


def test_research_admin_status_requires_admin(client):
    assert client.get("/api/v1/admin/research").status_code == 401
    login(client, "research-admin", "admin")
    result = client.get("/api/v1/admin/research")
    assert result.status_code == 200
    assert len(result.json()["sources"]) == 11
    assert result.json()["evaluation"]["results"]["hybrid"]["count"] == 12


def test_minimum_evidence_set_shared_document_and_unmapped():
    conditions = [
        {"id": "age", "status": "INSUFFICIENT_EVIDENCE", "required_documents": ["identity", "age_proof"]},
        {"id": "residence", "status": "INSUFFICIENT_EVIDENCE", "required_documents": ["identity", "residence_proof"]},
        {"id": "occupation", "status": "INSUFFICIENT_EVIDENCE", "required_documents": []},
    ]
    result = minimal_evidence_set(conditions)
    assert [(x["document_type"], x["resolves"]) for x in result["documents"]] == [("identity", ["age", "residence"])]
    assert result["no_sufficient_mapping"] == ["occupation"]


def test_source_change_flags_historical_assessment(client):
    with DB() as db:
        profile = db.scalar(select(Profile))
        assessment = Evaluation(profile_id=profile.id, results=[{"scheme_id": "demo-silver", "version": 1}])
        proposal = Proposal(scheme_id="demo-silver", base_version=1, old_text="income 50000", new_text="income 40000", classification="eligibility", proposed_rule={}, regression_cases=[])
        db.add_all([assessment, proposal])
        db.flush()
        impact = proposal_impact(db, proposal)
        assert set(impact["condition_ids"]) == {"age", "income", "residence"}
        assert impact["assessment_ids"] == [assessment.id]
