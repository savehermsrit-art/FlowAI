from app.research import ResearchIndex, load_corpus
from app.rag import Claim, GeneratedAnswer, _numeric_tokens
from app.rules import minimal_evidence_set
from app.db import DB, Evaluation, Profile, Proposal
from app.monitor import proposal_impact
from sqlalchemy import select
from conftest import login


def test_archived_sources_and_citations_resolve(monkeypatch):
    sources, passages, schemes = load_corpus()
    assert len(sources) == 11
    assert all(s["status"] == "fetched" for s in sources.values())
    assert len(schemes) == 3
    lookup = {p["id"]: p for p in passages}
    monkeypatch.setattr("app.rag._generate", lambda q, context, kn: (
        GeneratedAnswer(claims=[Claim(text="Age 65 years or older", citation_ids=[next(p["id"] for p in context if "65" in p["text"])], evidence_quote="65 ವರ್ಷದ ಅಥವಾ ಮೇಲ್ಪಟ್ಟ ವಯಸ್ಸಿನ ಹಿರಿಯ ಜೀವಗಳನ್ನು")], insufficient_evidence=False),
        "test model",
    ))
    answer = ResearchIndex().answer("What is the age requirement for Sandhya Suraksha?", "ka-sandhya")
    assert answer["status"] == "grounded_generation"
    assert "65" in answer["answer"]
    assert all(c["id"] in lookup and c["url"] == lookup[c["id"]]["url"] for c in answer["citations"])


def test_research_abstains_on_unsupported_question(client, monkeypatch):
    monkeypatch.setattr("app.rag._generate", lambda q, context, kn: (
        GeneratedAnswer(claims=[], insufficient_evidence=True), "test model",
    ))
    response = client.get("/api/v1/research/ask?q=What%20is%20the%20weather%20tomorrow%3F")
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["citations"] == []


def test_kannada_research_answer_has_official_passage(client, monkeypatch):
    monkeypatch.setattr("app.rag._generate", lambda q, context, kn: (
        GeneratedAnswer(claims=[Claim(text="ವಾರ್ಷಿಕ ಆದಾಯ ರೂ.32,000 ಮೀರಬಾರದು", citation_ids=[next(p["id"] for p in context if "32,000" in p["text"])], evidence_quote="ವಾರ್ಷಿಕ ಆದಾಯ ರೂ.32,000/- ಕ್ಕಿಂತ ಹೆಚ್ಚಿಗೆ ಇರಕೂಡದು")], insufficient_evidence=False),
        "test model",
    ))
    response = client.get("/api/v1/research/ask", params={"q": "ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಯೋಜನೆಗೆ ಆದಾಯ ಮಿತಿ ಎಷ್ಟು?"})
    assert response.status_code == 200
    result = response.json()
    assert result["citations"] and "32,000" in result["answer"]
    assert "dssp.karnataka.gov.in" in result["citations"][0]["url"]


def test_generation_rejects_fabricated_numbers_and_citations(monkeypatch):
    index = ResearchIndex()
    question = "What is the age requirement for Sandhya Suraksha?"
    def invented_number(q, context, kn):
        source = next(p for p in context if "65" in p["text"])
        return GeneratedAnswer(claims=[Claim(text="Age 99", citation_ids=[source["id"]], evidence_quote="65 ವರ್ಷದ ಅಥವಾ ಮೇಲ್ಪಟ್ಟ ವಯಸ್ಸಿನ ಹಿರಿಯ ಜೀವಗಳನ್ನು")], insufficient_evidence=False), "test model"
    monkeypatch.setattr("app.rag._generate", invented_number)
    assert index.answer(question, "ka-sandhya")["status"] == "unsupported_numbers"
    monkeypatch.setattr("app.rag._generate", lambda q, context, kn: (
        GeneratedAnswer(claims=[Claim(text="Age 65", citation_ids=["invented:source"], evidence_quote="65 ವರ್ಷದ")], insufficient_evidence=False), "test model"
    ))
    assert index.answer(question, "ka-sandhya")["status"] == "invalid_citations"
    monkeypatch.setattr("app.rag._generate", lambda q, context, kn: (
        GeneratedAnswer(claims=[Claim(text="Age 65", citation_ids=[next(p["id"] for p in context if "65" in p["text"])], evidence_quote="this quote is not in the source")], insufficient_evidence=False), "test model"
    ))
    assert index.answer(question, "ka-sandhya")["status"] == "unsupported_quote"


def test_generation_failure_is_visible(monkeypatch):
    monkeypatch.setattr("app.rag._generate", lambda q, context, kn: (_ for _ in ()).throw(ValueError("model offline")))
    result = ResearchIndex().answer("What is the age requirement for Sandhya Suraksha?", "ka-sandhya")
    assert result["status"] == "generator_unavailable"
    assert result["citations"] == []
    assert "model offline" in result["model_status"]


def test_generated_absence_claim_abstains(monkeypatch):
    monkeypatch.setattr("app.rag._generate", lambda q, context, kn: (
        GeneratedAnswer(claims=[Claim(text="The weather is not specified in the sources", citation_ids=[context[0]["id"]], evidence_quote=context[0]["text"][:20])], insufficient_evidence=False), "test model"
    ))
    result = ResearchIndex().answer("What is the weather tomorrow?")
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []


def test_numeric_source_separator_normalization():
    assert _numeric_tokens("ರೂ.10.000") == _numeric_tokens("₹10,000")
    assert _numeric_tokens("2.5") != _numeric_tokens("25")


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
