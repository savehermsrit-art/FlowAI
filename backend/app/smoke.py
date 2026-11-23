"""Exercise the running services without mocks. Uses fictional data and deletes the profile."""

import json
import os
import time
from pathlib import Path

import httpx
from sqlalchemy import text
from . import storage
from .db import engine
from .documents import synthetic_png, synthetic_pdf


def run():
    root = Path(os.getenv("DATA_DIR", "data"))
    root.mkdir(exist_ok=True)
    results = {}
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    with httpx.Client(base_url=base, headers={"X-FormFlow": "1"}, timeout=70) as c:

        def post(path, **kwargs):
            r = c.post("/api/v1" + path, **kwargs)
            r.raise_for_status()
            return r.json()

        def get(path):
            r = c.get("/api/v1" + path)
            r.raise_for_status()
            return r.json()

        health = c.get("/health")
        health.raise_for_status()
        results["database"] = health.json()["database"]
        challenge = post("/auth/request-otp", json={"handle": f"smoke-{time.time_ns()}", "role": "citizen"})
        post(
            "/auth/verify-otp", json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]}
        )
        p = post("/profiles", json={"name": "Fictional live integration smoke", "language": "en"})["id"]
        try:
            results["consent_blocks_assessment"] = c.post(f"/api/v1/profiles/{p}/evaluations").status_code == 409
            post(f"/profiles/{p}/consent", json={"accepted": True, "notice_version": "2026-11-v1"})
            ids = []
            for category in ("age_proof", "residence", "income"):
                payload = synthetic_png() if category == "age_proof" else synthetic_pdf("A", category)
                item = post(
                    f"/profiles/{p}/documents?category={category}",
                    files={"file": ("FICTIONAL.png" if category == "age_proof" else "FICTIONAL.pdf", payload)},
                )
                ids.append(item["document"]["id"])
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                docs = get(f"/profiles/{p}/documents")
                if all(d["status"] == "ready" for d in docs):
                    break
                if any(d["status"] == "failed" for d in docs):
                    raise RuntimeError("Document processing failed")
                time.sleep(0.5)
            else:
                raise RuntimeError("Worker did not finish within 60 seconds")
            results["background_jobs"] = True
            fs = get(f"/profiles/{p}/facts")
            results["real_tesseract"] = any(
                f["method"] == "tesseract_eng_kan" and f["key"] == "age" and f["value"] == "70" for f in fs
            )
            for f in fs:
                post(f"/facts/{f['id']}/review", json={"action": "confirmed"})
            e = post(f"/profiles/{p}/evaluations")
            results["eligible"] = all(r["verdict"] == "LIKELY_ELIGIBLE" for r in e["results"])
            region = c.get(f"/api/v1/facts/{fs[0]['id']}/region")
            results["document_region"] = region.status_code == 200 and region.content.startswith(b"\x89PNG")
            pdf = c.get(f"/api/v1/evaluations/{e['id']}/report?language=kn")
            pdf.raise_for_status()
            (root / "verified-report-kn.pdf").write_bytes(pdf.content)
            results["kannada_pdf"] = pdf.content.startswith(b"%PDF")
            results["full_text_retrieval"] = bool(get("/search?q=income"))
            if os.getenv("MINIO_ENDPOINT"):
                obj = storage.client().get_object(Bucket="documents", Key=ids[0])["Body"].read()
                results["minio_ciphertext"] = obj.startswith(b"gAAAA") and b"FICTIONAL" not in obj
            with engine.connect() as conn:
                results["migration"] = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                if engine.dialect.name == "postgresql":
                    results["pgvector_extension"] = bool(
                        conn.execute(text("SELECT 1 FROM pg_extension WHERE extname='vector'")).scalar()
                    )
        finally:
            deleted = c.delete(f"/api/v1/profiles/{p}")
            deleted.raise_for_status()
            results["deletion"] = c.get(f"/api/v1/profiles/{p}").status_code == 404
            if os.getenv("MINIO_ENDPOINT"):
                remaining = storage.client().list_objects_v2(Bucket="documents").get("Contents", [])
                results["objects_removed"] = not ({o["Key"] for o in remaining} & set(ids))
        challenge = post(
            "/auth/request-otp",
            json={
                "handle": f"smoke-admin-{time.time_ns()}",
                "role": "admin",
                "admin_access": (root / "admin-access.txt").read_text().strip(),
            },
        )
        post(
            "/auth/verify-otp", json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]}
        )
        post("/admin/monitor")
        sources = get("/admin/overview")["sources"]
        results["official_source_monitor"] = [
            {"id": s["id"], "snapshots": len(s["snapshots"]), "error": s["last_error"]}
            for s in sources
            if not s["url"].startswith("fixture://")
        ]
    (root / "live-smoke.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    required = [v for k, v in results.items() if isinstance(v, bool)]
    if not all(required):
        raise RuntimeError("A live integration check failed; see live-smoke.json")
    return results


if __name__ == "__main__":
    run()
