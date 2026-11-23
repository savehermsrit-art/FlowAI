import io
from datetime import timedelta

import fitz
from PIL import Image
from sqlalchemy import select

from conftest import login
from app import storage
from app.db import DB, Document, Fact, Evaluation, RuleVersion, now
from app.documents import inspect, synthetic_pdf
from app.main import PREFIX as P
from app.worker import cleanup


def create(client, name="Fictional test"):
    r = client.post(P + "/profiles", json={"name": name, "language": "en", "authorized": True})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def consent(client, p):
    r = client.post(f"{P}/profiles/{p}/consent", json={"accepted": True, "notice_version": "2026-11-v1"})
    assert r.status_code == 200


def upload(client, p, category, case="A"):
    r = client.post(
        f"{P}/profiles/{p}/documents?category={category}",
        files={"file": ("../fake.pdf", synthetic_pdf(case, category), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_auth_one_time_expiry_csrf_and_admin(client):
    assert client.get(P + "/profiles").status_code == 401
    assert client.post(P + "/auth/request-otp", json={"handle": "bob"}, headers={"X-FormFlow": ""}).status_code == 403
    assert client.post(P + "/auth/request-otp", json={"handle": "bob", "role": "admin"}).status_code == 403
    ch = client.post(P + "/auth/request-otp", json={"handle": "bob"}).json()
    assert (
        client.post(P + "/auth/verify-otp", json={"challenge_id": ch["challenge_id"], "code": "x12345"}).status_code
        == 401
    )
    payload = {"challenge_id": ch["challenge_id"], "code": ch["development_code"]}
    assert client.post(P + "/auth/verify-otp", json=payload).status_code == 200
    assert client.post(P + "/auth/verify-otp", json=payload).status_code == 401
    assert client.get(P + "/admin/overview").status_code == 403
    client.post(P + "/auth/logout")
    assert client.get(P + "/auth/me").status_code == 401


def test_ownership_caregiver_consent(citizen):
    c = citizen
    p = create(c)
    assert c.post(f"{P}/profiles/{p}/evaluations").status_code == 409
    assert (
        c.post(f"{P}/profiles/{p}/documents", files={"file": ("x.pdf", synthetic_pdf("A", "age_proof"))}).status_code
        == 409
    )
    consent(c, p)
    doc = upload(c, p, "age_proof")["document"]["id"]
    login(c, "another-carer", "caregiver")
    assert c.post(P + "/profiles", json={"name": "Fictional", "authorized": False}).status_code == 422
    assert c.get(f"{P}/profiles/{p}").status_code == 404
    assert c.get(f"{P}/documents/{doc}/content").status_code == 404
    assert c.delete(f"{P}/profiles/{p}").status_code == 404
    own = create(c)
    assert c.get(f"{P}/profiles/{own}").status_code == 200


def test_full_journey_export_correction_and_deletion(citizen):
    c = citizen
    p = create(c)
    consent(c, p)
    ids = []
    for typ in ("age_proof", "residence", "income"):
        item = upload(c, p, typ)
        ids.append(item["document"]["id"])
        assert c.get(P + "/jobs/" + item["job_id"]).json()["state"] == "complete"
    fs = c.get(f"{P}/profiles/{p}/facts").json()
    assert {f["key"] for f in fs} == {"age", "state", "annual_income"}
    region = c.get(f"{P}/facts/{fs[0]['id']}/region")
    assert region.status_code == 200 and region.content.startswith(b"\x89PNG")
    preview = c.get(f"{P}/documents/{ids[0]}/preview/1")
    assert preview.status_code == 200 and preview.content.startswith(b"\x89PNG")
    assert c.get(f"{P}/documents/{ids[0]}/preview/2").status_code == 404
    assert c.post(f"{P}/profiles/{p}/evaluations").json()["results"][0]["verdict"] == "NEEDS_EVIDENCE"
    for f in fs:
        assert c.post(f"{P}/facts/{f['id']}/review", json={"action": "confirmed"}).status_code == 200
    e = c.post(f"{P}/profiles/{p}/evaluations").json()
    assert e["results"][0]["verdict"] == "LIKELY_ELIGIBLE"
    assert e["results"][0]["conditions"][0]["evidence"][0]["document_id"] in ids
    pdf = c.get(f"{P}/evaluations/{e['id']}/report?language=kn")
    assert pdf.status_code == 200, pdf.text[:100]
    assert pdf.content.startswith(b"%PDF")
    report = fitz.open(stream=pdf.content, filetype="pdf")
    assert len(report) >= 1
    output = storage.ROOT / "report-kn.pdf"
    output.write_bytes(pdf.content)
    report[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(str(storage.ROOT / "report-kn.png"))
    income = next(f for f in fs if f["key"] == "annual_income")
    assert c.post(f"{P}/facts/{income['id']}/review", json={"action": "corrected", "value": "20000"}).status_code == 200
    assert c.post(f"{P}/facts/{income['id']}/review", json={"action": "confirmed"}).status_code == 409
    assert c.post(f"{P}/profiles/{p}/evaluations").json()["results"][0]["verdict"] == "NEEDS_EVIDENCE"
    with DB() as db:
        assert db.get(Fact, income["id"]).original == "30000"
    encrypted = (storage.ROOT / (ids[0] + ".enc")).read_bytes()
    assert not encrypted.startswith(b"%PDF") and b"Fictional" not in encrypted
    assert c.delete(f"{P}/profiles/{p}").status_code == 200
    assert c.get(f"{P}/documents/{ids[0]}").status_code == 404
    assert not (storage.ROOT / (ids[0] + ".enc")).exists()
    with DB() as db:
        assert not list(db.scalars(select(Fact))) and not list(db.scalars(select(Evaluation)))


def test_missing_and_failing_demo(citizen):
    for case, expected in (("B", "NEEDS_EVIDENCE"), ("C", "NOT_ELIGIBLE")):
        p = create(citizen, case)
        consent(citizen, p)
        for typ in ("age_proof", "residence") if case == "B" else ("age_proof", "residence", "income"):
            upload(citizen, p, typ, case)
        for f in citizen.get(f"{P}/profiles/{p}/facts").json():
            citizen.post(f"{P}/facts/{f['id']}/review", json={"action": "confirmed"})
        assert citizen.post(f"{P}/profiles/{p}/evaluations").json()["results"][0]["verdict"] == expected


def test_retention_and_revoke(citizen):
    p = create(citizen)
    consent(citizen, p)
    doc = upload(citizen, p, "income")["document"]["id"]
    citizen.post(f"{P}/profiles/{p}/evaluations")
    with DB() as db:
        db.get(Document, doc).expires_at = now() - timedelta(days=1)
        db.commit()
    assert cleanup() == 1
    assert citizen.get(f"{P}/profiles/{p}/facts").json() == []
    assert citizen.get(f"{P}/profiles/{p}/evaluations").json() == []
    citizen.post(f"{P}/profiles/{p}/consent/revoke")
    assert citizen.post(f"{P}/profiles/{p}/evaluations").status_code == 409


def test_upload_inspection(citizen):
    p = create(citizen)
    consent(citizen, p)
    assert (
        citizen.post(
            f"{P}/profiles/{p}/documents", files={"file": ("x.png", b"<script>alert(1)</script>", "image/png")}
        ).status_code
        == 422
    )
    assert (
        citizen.post(f"{P}/profiles/{p}/documents", files={"file": ("x.pdf", b"%PDF-not-a-document")}).status_code
        == 422
    )
    pdf = fitz.open()
    for _ in range(11):
        pdf.new_page()
    import pytest

    with pytest.raises(ValueError):
        inspect(pdf.tobytes())
    image = Image.new("RGB", (100, 100), "white")
    b = io.BytesIO()
    image.save(b, format="PNG")
    assert inspect(b.getvalue()) == "image/png"


def test_admin_publication_and_history(client):
    login(client)
    p = create(client)
    consent(client, p)
    old = client.post(f"{P}/profiles/{p}/evaluations").json()
    login(client, "local-admin", "admin")
    assert client.get(P + "/admin/overview").status_code == 200
    proposal = client.post(P + "/admin/simulate-change").json()["id"]
    with DB() as db:
        assert db.get(RuleVersion, "demo-silver:2") is None
    response = client.post(f"{P}/admin/proposals/{proposal}/approve")
    assert response.status_code == 200, response.text
    assert response.json()["validation"]["regression_passed"] == 4
    assert client.post(f"{P}/admin/proposals/{proposal}/approve").status_code == 409
    with DB() as db:
        assert db.get(RuleVersion, "demo-silver:1") and db.get(RuleVersion, "demo-silver:2")
    login(client)
    history = client.get(f"{P}/profiles/{p}/evaluations").json()
    assert history[0]["rules_changed"] and history[0]["results"] == old["results"]


def test_unvalidated_publication_rejected(client):
    login(client, "admin-test", "admin")
    proposal = client.post(P + "/admin/simulate-change").json()["id"]
    data = client.get(P + "/admin/overview").json()["proposals"][0]
    data["proposed_rule"]["conditions"][0]["value"] = None
    client.patch(
        f"{P}/admin/proposals/{proposal}",
        json={"proposed_rule": data["proposed_rule"], "regression_cases": data["regression_cases"]},
    )
    assert client.post(f"{P}/admin/proposals/{proposal}/approve").status_code == 422
    assert client.post(f"{P}/admin/proposals/{proposal}/reject").json()["state"] == "rejected"


def test_retrieval_and_human_labels(client):
    assert client.get(P + "/search?q=income").json()
    schemes = client.get(P + "/schemes").json()
    assert all(s["active_version"] is None for s in schemes if s["mode"] == "REVIEWED")
    login(client, "researcher", "admin")
    assert client.get(P + "/admin/evaluation").json()["count"] == 52
    csv = b"id,verdict\nenglish_clear:eligible,LIKELY_ELIGIBLE\n"
    r = client.post(P + "/admin/human-labels", files={"file": ("labels.csv", csv)})
    assert r.json()["agreement"] == 1


def test_source_management_and_snapshot(client):
    login(client, "source-admin", "admin")
    payload = {"id": "official-test", "scheme_id": "ka-sandhya", "url": "http://127.0.0.1/private"}
    assert client.post(P + "/admin/sources", json=payload).status_code == 422
    payload["url"] = "https://vijayapura.nic.in/en/service/social-security-pensions/"
    assert client.post(P + "/admin/sources", json=payload).status_code == 200
    proposal = client.post(P + "/admin/simulate-change").json()["id"]
    snapshot_id = next(s for s in client.get(P + "/admin/overview").json()["sources"] if s["id"] == "demo-silver")[
        "snapshots"
    ][0]["id"]
    snapshot = client.get(P + "/admin/snapshots/" + snapshot_id).json()
    assert snapshot["content_hash"] and "FICTIONAL" in snapshot["text"]
    assert client.post(f"{P}/admin/proposals/{proposal}/reject").status_code == 200
