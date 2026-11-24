import hashlib
import json
import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, timedelta, timezone
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text, delete as sql_delete
from sqlalchemy.orm import Session as SqlSession

from . import storage
from .db import (
    engine,
    get_db,
    User,
    Session,
    Otp,
    Profile,
    Consent,
    Document,
    Job,
    Fact,
    Confirmation,
    Scheme,
    RuleVersion,
    Evaluation,
    Source,
    Clause,
    Snapshot,
    Proposal,
    Audit,
    now,
)
from .documents import inspect, synthetic_pdf, synthetic_png
from .rules import Rule, evaluate, rank
from .seed import seed, seed_profiles
from .worker import process, cleanup
from .research import ResearchIndex
from .monitor import proposal_impact
from functools import lru_cache

DEV = os.getenv("DEVELOPMENT", "true").lower() == "true"
MODE = os.getenv("FORMFLOW_MODE", "DEMO")
COOKIE = "formflow_session"
PREFIX = "/api/v1"


def admin_key():
    p = storage.ROOT / "admin-access.txt"
    if not p.exists():
        p.write_text(secrets.token_urlsafe(24), encoding="utf-8")
    return p.read_text(encoding="utf-8").strip()


@asynccontextmanager
async def lifespan(app):
    if not DEV:
        # No scanner is configured in this controlled-demonstration build.
        raise RuntimeError("Non-development operation disabled: malware scanner and legal/security review required")
    admin_key()
    seed()
    seed_profiles()
    yield


app = FastAPI(title="FormFlow AI · Local demonstration", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-FormFlow"],
)
rates = defaultdict(deque)


@app.middleware("http")
async def guards(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("x-formflow") != "1":
            return JSONResponse({"detail": "CSRF header required"}, status_code=403)
        if request.headers.get("origin") not in (
            None,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
        ):
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    ip = request.client.host if request.client else "local"
    key = (ip, "auth" if "/auth/" in request.url.path else "api")
    queue = rates[key]
    stamp = time.monotonic()
    while queue and queue[0] < stamp - 60:
        queue.popleft()
    if len(queue) >= (30 if key[1] == "auth" else 300):
        return JSONResponse({"detail": "Too many requests. Please wait one minute."}, status_code=429)
    queue.append(stamp)
    response = await call_next(request)
    response.headers.update(
        {
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
            "Cache-Control": "no-store",
            "X-Frame-Options": "DENY",
        }
    )
    return response


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def user(request: Request, db: SqlSession = Depends(get_db)):
    token = request.cookies.get(COOKIE, "")
    session = db.get(Session, sha(token))
    if not token or not session or utc(session.expires) < now():
        raise HTTPException(401, "Please sign in")
    return db.get(User, session.user_id)


def admin(u=Depends(user)):
    if u.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return u


def owned(db, profile_id, u):
    p = db.get(Profile, profile_id)
    if not p or p.owner_id != u.id:
        raise HTTPException(404, "Profile not found")
    return p


def require_consent(db, profile_id):
    c = db.scalar(select(Consent).where(Consent.profile_id == profile_id).order_by(Consent.created_at.desc()))
    if not c or not c.accepted:
        raise HTTPException(409, "Explicit consent is required before processing or assessment")


def audit(db, u, action, target):
    db.add(Audit(actor_id=u.id, action=action, target_id=target))


def fields(obj, names):
    return {k: getattr(obj, k) for k in names.split()}


def document_json(doc):
    return fields(doc, "id profile_id category content_type status error quality expires_at created_at")


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(StrictInput):
    handle: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9_.@-]+$")
    role: Literal["citizen", "caregiver", "admin"] = "citizen"
    admin_access: str = ""


class Verify(StrictInput):
    challenge_id: str
    code: str = Field(min_length=6, max_length=6)


class ProfileInput(StrictInput):
    name: str = Field(min_length=1, max_length=80)
    language: Literal["en", "kn"] = "en"
    authorized: bool = False


class ConsentInput(StrictInput):
    accepted: bool
    notice_version: Literal["2026-11-v1"] = "2026-11-v1"


class ReviewInput(StrictInput):
    action: Literal["confirmed", "corrected", "unreadable", "removed"]
    value: str | None = Field(default=None, max_length=100)


@app.get("/health")
def health(db: SqlSession = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "mode": MODE, "development": DEV, "database": engine.dialect.name}


@app.get(PREFIX + "/capabilities")
def capabilities():
    import shutil
    import pytesseract

    try:
        languages = pytesseract.get_languages(config="")
    except Exception:
        languages = []
    return {
        "mode": MODE,
        "ocr_languages": languages,
        "tesseract": bool(shutil.which("tesseract")),
        "local_llm": False,
        "semantic_search": False,
        "malware_scanner": False,
        "development_only": True,
        "retention_days": int(os.getenv("RETENTION_DAYS", "30")),
    }


@app.post(PREFIX + "/auth/request-otp")
def request_otp(body: Login, db: SqlSession = Depends(get_db)):
    if not DEV:
        raise HTTPException(403, "Local demonstration authentication disabled")
    handle = body.handle.casefold()
    existing = db.scalar(select(User).where(User.handle == handle))
    if body.role == "admin" and not secrets.compare_digest(body.admin_access, admin_key()):
        raise HTTPException(403, "Use the local admin access file")
    if existing and existing.role != body.role:
        raise HTTPException(409, "This account has a different role")
    # Invalidate outstanding challenges for this account.
    db.execute(sql_delete(Otp).where(Otp.handle == handle))
    code = f"{secrets.randbelow(1000000):06d}"
    otp = Otp(handle=handle, role=body.role, code_hash=sha(code), expires=now() + timedelta(minutes=5))
    db.add(otp)
    db.commit()
    return {
        "challenge_id": otp.id,
        "development_code": code,
        "channel": "LOCAL DEVELOPMENT ONLY · expires in five minutes",
    }


@app.post(PREFIX + "/auth/verify-otp")
def verify_otp(body: Verify, response: Response, db: SqlSession = Depends(get_db)):
    otp = db.get(Otp, body.challenge_id)
    if not otp or utc(otp.expires) < now() or otp.attempts >= 5:
        raise HTTPException(401, "Expired or invalid challenge")
    otp.attempts += 1
    db.commit()
    if not secrets.compare_digest(sha(body.code), otp.code_hash):
        raise HTTPException(401, "Incorrect code")
    u = db.scalar(select(User).where(User.handle == otp.handle))
    if not u:
        u = User(handle=otp.handle, role=otp.role)
        db.add(u)
        db.flush()
    token = secrets.token_urlsafe(40)
    db.add(Session(token_hash=sha(token), user_id=u.id, expires=now() + timedelta(hours=8)))
    db.delete(otp)
    audit(db, u, "login", u.id)
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=not DEV, max_age=8 * 3600, path="/")
    return fields(u, "id handle role")


@app.get(PREFIX + "/auth/me")
def me(u=Depends(user)):
    return fields(u, "id handle role")


@app.post(PREFIX + "/auth/logout")
def logout(request: Request, response: Response, db: SqlSession = Depends(get_db)):
    db.execute(sql_delete(Session).where(Session.token_hash == sha(request.cookies.get(COOKIE, ""))))
    db.commit()
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get(PREFIX + "/profiles")
def profiles(u=Depends(user), db: SqlSession = Depends(get_db)):
    return [
        fields(p, "id name language fictional authorization")
        for p in db.scalars(select(Profile).where(Profile.owner_id == u.id))
    ]


@app.post(PREFIX + "/profiles")
def create_profile(body: ProfileInput, u=Depends(user), db: SqlSession = Depends(get_db)):
    if u.role == "admin":
        raise HTTPException(403, "Use a citizen or caregiver account")
    if u.role == "caregiver" and not body.authorized:
        raise HTTPException(422, "Caregiver authorization must be explicitly confirmed")
    p = Profile(
        owner_id=u.id,
        name=body.name,
        language=body.language,
        authorization="caregiver attestation" if u.role == "caregiver" else "self",
    )
    db.add(p)
    db.flush()
    audit(db, u, "profile_created", p.id)
    db.commit()
    return fields(p, "id name language fictional authorization")


@app.get(PREFIX + "/profiles/{profile_id}")
def get_profile(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    return fields(owned(db, profile_id, u), "id name language fictional authorization")


@app.patch(PREFIX + "/profiles/{profile_id}")
def update_profile(profile_id: str, body: ProfileInput, u=Depends(user), db: SqlSession = Depends(get_db)):
    p = owned(db, profile_id, u)
    p.name, p.language = body.name, body.language
    db.commit()
    return fields(p, "id name language fictional authorization")


@app.get(PREFIX + "/profiles/{profile_id}/consent")
def consent_status(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    owned(db, profile_id, u)
    c = db.scalar(select(Consent).where(Consent.profile_id == profile_id).order_by(Consent.created_at.desc()))
    return fields(c, "accepted version purpose created_at") if c else {"accepted": False, "version": "2026-11-v1"}


@app.post(PREFIX + "/profiles/{profile_id}/consent")
def consent(profile_id: str, body: ConsentInput, u=Depends(user), db: SqlSession = Depends(get_db)):
    owned(db, profile_id, u)
    db.add(Consent(profile_id=profile_id, accepted=body.accepted, version=body.notice_version))
    audit(db, u, "consent_accepted" if body.accepted else "consent_revoked", profile_id)
    db.commit()
    return {"accepted": body.accepted}


@app.post(PREFIX + "/profiles/{profile_id}/consent/revoke")
def revoke(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    return consent(profile_id, ConsentInput(accepted=False), u, db)


@app.post(PREFIX + "/profiles/{profile_id}/documents")
async def upload(
    profile_id: str,
    background: BackgroundTasks,
    category: str = "other",
    file: UploadFile = File(...),
    u=Depends(user),
    db: SqlSession = Depends(get_db),
):
    owned(db, profile_id, u)
    require_consent(db, profile_id)
    if category not in ("age_proof", "income", "residence", "identity", "disability", "pension", "other"):
        raise HTTPException(422, "Unsupported document category")
    content = await file.read(12 * 1024 * 1024 + 1)
    try:
        content_type = inspect(content)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    doc = Document(
        profile_id=profile_id,
        category=category,
        content_type=content_type,
        expires_at=now() + timedelta(days=int(os.getenv("RETENTION_DAYS", "30"))),
    )
    db.add(doc)
    db.flush()
    storage.put(doc.id, content)
    job = Job(document_id=doc.id)
    db.add(job)
    audit(db, u, "document_uploaded", doc.id)
    db.commit()
    if os.getenv("REDIS_URL"):
        try:
            process.delay(doc.id)
        except Exception:
            doc.status, job.state, doc.error = "failed", "failed", "QUEUE_UNAVAILABLE"
            db.commit()
    else:
        background.add_task(process, doc.id)
    return {"document": document_json(doc), "job_id": job.id}


@app.get(PREFIX + "/profiles/{profile_id}/documents")
def documents(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    owned(db, profile_id, u)
    return [
        document_json(d)
        for d in db.scalars(select(Document).where(Document.profile_id == profile_id).order_by(Document.created_at))
    ]


def own_document(db, document_id, u):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    owned(db, doc.profile_id, u)
    return doc


@app.get(PREFIX + "/documents/{document_id}")
def document(document_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    return document_json(own_document(db, document_id, u))


@app.get(PREFIX + "/documents/{document_id}/content")
def content(document_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    doc = own_document(db, document_id, u)
    return Response(
        storage.get(doc.id),
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'inline; filename="document-{doc.id}.{"pdf" if doc.content_type == "application/pdf" else "png"}"'
        },
    )


@app.delete(PREFIX + "/documents/{document_id}")
def delete_document(document_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    doc = own_document(db, document_id, u)
    storage.delete(doc.id)
    db.execute(sql_delete(Evaluation).where(Evaluation.profile_id == doc.profile_id))
    db.delete(doc)
    audit(db, u, "document_deleted", document_id)
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/documents/{document_id}/preview/{page_number}")
def document_preview(document_id: str, page_number: int, u=Depends(user), db: SqlSession = Depends(get_db)):
    import pymupdf

    doc = own_document(db, document_id, u)
    if doc.content_type != "application/pdf":
        if page_number != 1:
            raise HTTPException(404, "Page not found")
        return Response(storage.get(doc.id), media_type=doc.content_type)
    with pymupdf.open(stream=storage.get(doc.id), filetype="pdf") as pdf:
        if not 1 <= page_number <= len(pdf):
            raise HTTPException(404, "Page not found")
        pix = pdf[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5))
        return Response(pix.tobytes("png"), media_type="image/png")


@app.get(PREFIX + "/jobs/{job_id}")
def job(job_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    j = db.get(Job, job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    own_document(db, j.document_id, u)
    return fields(j, "id document_id state error")


def fact_json(f, doc):
    return dict(
        fields(f, "id document_id key original value confidence page bbox method review issued_at expires_at"),
        document_type=doc.category,
        document_validation="unverified; not authenticated",
    )


@app.get(PREFIX + "/profiles/{profile_id}/facts")
def facts(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    owned(db, profile_id, u)
    return [
        fact_json(f, db.get(Document, f.document_id))
        for f in db.scalars(select(Fact).where(Fact.profile_id == profile_id))
    ]


@app.get(PREFIX + "/facts/{fact_id}/region")
def fact_region(fact_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    import io
    import pymupdf
    from PIL import Image

    f = db.get(Fact, fact_id)
    if not f:
        raise HTTPException(404, "Fact not found")
    doc = own_document(db, f.document_id, u)
    content = storage.get(doc.id)
    scale = 1
    if doc.content_type == "application/pdf":
        with pymupdf.open(stream=content, filetype="pdf") as pdf:
            page = pdf[f.page - 1]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            scale = 2
    else:
        image = Image.open(io.BytesIO(content)).convert("RGB")
    if len(f.bbox) == 4:
        x0, y0, x1, y1 = [v * scale for v in f.bbox]
        bounds = (max(0, x0 - 35), max(0, y0 - 30), min(image.width, x1 + 35), min(image.height, y1 + 30))
        if bounds[2] > bounds[0] and bounds[3] > bounds[1]:
            image = image.crop(bounds)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return Response(output.getvalue(), media_type="image/png")


@app.post(PREFIX + "/facts/{fact_id}/review")
def review(fact_id: str, body: ReviewInput, u=Depends(user), db: SqlSession = Depends(get_db)):
    f = db.get(Fact, fact_id)
    if not f:
        raise HTTPException(404, "Fact not found")
    owned(db, f.profile_id, u)
    # A correction cannot subsequently be upgraded to document-backed evidence by pressing Confirm.
    if body.action == "confirmed" and db.scalar(
        select(Confirmation).where(Confirmation.fact_id == f.id, Confirmation.action == "corrected")
    ):
        raise HTTPException(409, "Corrected values require replacement supporting evidence")
    if body.action == "corrected" and not body.value:
        raise HTTPException(422, "Correction value required")
    f.review = body.action
    if body.action == "corrected":
        f.value = body.value
    db.add(Confirmation(fact_id=f.id, user_id=u.id, action=body.action, value=f.value))
    audit(db, u, "fact_reviewed", f.id)
    db.commit()
    return fact_json(f, db.get(Document, f.document_id))


@app.get(PREFIX + "/schemes")
def schemes(db: SqlSession = Depends(get_db)):
    return [dict(s.metadata_json, active_version=s.active_version) for s in db.scalars(select(Scheme))]


@lru_cache(maxsize=1)
def research_index():
    return ResearchIndex()


@app.get(PREFIX + "/research/schemes")
def research_schemes():
    index = research_index()
    passages = {p["id"]: p for p in index.passages}
    return [
        dict(scheme, **{
            category: [dict(field, value_kn=" ".join(passages[ref]["text"] for ref in field["passages"])) for field in scheme[category]]
            for category in ("eligibility", "exceptions", "benefits", "application_documents", "application")
        })
        for scheme in index.schemes
    ]


@app.get(PREFIX + "/research/status")
def research_status():
    index = research_index()
    return {"sources": list(index.sources.values()), "passage_count": len(index.passages), "model_error": index.model_error, "dense_model": os.getenv("FORMFLOW_EMBED_MODEL") or None, "reranker_model": os.getenv("FORMFLOW_RERANK_MODEL") or None, "generation_provider": os.getenv("FORMFLOW_LLM_PROVIDER", "ollama"), "generation_model": os.getenv("FORMFLOW_LLM_MODEL", "qwen3:4b")}


@app.get(PREFIX + "/admin/research")
def admin_research(u=Depends(admin)):
    from .research import ROOT
    status = research_status()
    report = ROOT / "evaluation.json"
    status["evaluation"] = json.loads(report.read_text()) if report.exists() else None
    return status


@app.get(PREFIX + "/research/ask")
def research_ask(q: str = "", scheme_id: str | None = None):
    if len(q.strip()) < 3 or len(q) > 500:
        raise HTTPException(422, "Question must contain 3–500 characters")
    if scheme_id and scheme_id not in {s["id"] for s in research_index().schemes}:
        raise HTTPException(404, "Scheme not in reviewed research corpus")
    return research_index().answer(q, scheme_id)


@app.get(PREFIX + "/search")
def search(q: str = "", db: SqlSession = Depends(get_db)):
    q = q[:150]
    if engine.dialect.name == "postgresql" and q.strip():
        rows = db.execute(
            text(
                "SELECT id, scheme_id, text, language FROM source_clauses WHERE to_tsvector('simple', text) @@ plainto_tsquery('simple', :q) ORDER BY ts_rank(to_tsvector('simple', text), plainto_tsquery('simple', :q)) DESC, id LIMIT 20"
            ),
            {"q": q},
        ).mappings()
        return [dict(r) for r in rows]
    return [
        fields(c, "id scheme_id text language")
        for c in db.scalars(select(Clause).where(Clause.text.ilike("%" + q + "%")).limit(20))
    ]


@app.post(PREFIX + "/profiles/{profile_id}/evaluations")
def assess(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    owned(db, profile_id, u)
    require_consent(db, profile_id)
    fs = [
        fact_json(f, db.get(Document, f.document_id))
        for f in db.scalars(select(Fact).where(Fact.profile_id == profile_id, Fact.review != "removed"))
    ]
    results = []
    for scheme in db.scalars(select(Scheme).where(Scheme.active_version.is_not(None))):
        if scheme.metadata_json["mode"] != MODE:
            continue
        version = db.get(RuleVersion, f"{scheme.id}:{scheme.active_version}")
        result = evaluate(Rule.model_validate(version.rule), fs, date.today())
        result.update(
            {
                k: v
                for k, v in scheme.metadata_json.items()
                if k in ("name", "name_kn", "description", "department", "category")
            }
        )
        results.append(result)
    e = Evaluation(profile_id=profile_id, results=rank(results))
    db.add(e)
    db.flush()
    audit(db, u, "assessment_created", e.id)
    db.commit()
    return fields(e, "id results created_at")


@app.get(PREFIX + "/profiles/{profile_id}/evaluations")
def history(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    owned(db, profile_id, u)
    output = []
    for e in db.scalars(
        select(Evaluation).where(Evaluation.profile_id == profile_id).order_by(Evaluation.created_at.desc())
    ):
        row = fields(e, "id results created_at")
        row["rules_changed"] = any(db.get(Scheme, r["scheme_id"]).active_version != r["version"] for r in e.results)
        output.append(row)
    return output


@app.get(PREFIX + "/evaluations/{evaluation_id}/report")
def report(evaluation_id: str, language: Literal["en", "kn"] = "en", u=Depends(user), db: SqlSession = Depends(get_db)):
    from .reports import report_pdf

    e = db.get(Evaluation, evaluation_id)
    if not e:
        raise HTTPException(404, "Assessment not found")
    p = owned(db, e.profile_id, u)
    return Response(
        report_pdf(p.name, e, language),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="FormFlow-preliminary-assessment.pdf"'},
    )


@app.delete(PREFIX + "/profiles/{profile_id}")
def delete_profile(profile_id: str, u=Depends(user), db: SqlSession = Depends(get_db)):
    p = owned(db, profile_id, u)
    for doc in db.scalars(select(Document).where(Document.profile_id == p.id)):
        storage.delete(doc.id)
    db.delete(p)
    audit(db, u, "profile_deleted", profile_id)
    db.commit()
    return {
        "ok": True,
        "policy": "Documents, facts, consent, confirmations and assessments deleted. Minimal action/ID audit retained; no document content.",
    }


@app.get(PREFIX + "/demo/document/{case}/{category}")
def demo_document(
    case: Literal["A", "B", "C"],
    category: Literal["age_proof", "income", "residence"],
    format: Literal["pdf", "png"] = "pdf",
    language: Literal["en", "kn"] = "en",
):
    if format == "png":
        return Response(
            synthetic_png(case, language),
            media_type="image/png",
            headers={"Content-Disposition": 'attachment; filename="FICTIONAL-sample.png"'},
        )
    return Response(
        synthetic_pdf(case, category),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="FICTIONAL-{case}-{category}.pdf"'},
    )


@app.get(PREFIX + "/admin/overview")
def overview(u=Depends(admin), db: SqlSession = Depends(get_db)):
    return {
        "sources": [
            dict(
                fields(s, "id scheme_id url last_error"),
                snapshots=[
                    fields(x, "id content_hash created_at")
                    for x in db.scalars(select(Snapshot).where(Snapshot.source_id == s.id))
                ],
            )
            for s in db.scalars(select(Source))
        ],
        "proposals": [
            dict(fields(
                p,
                "id scheme_id base_version old_text new_text classification proposed_rule regression_cases state validation reviewed_by created_at",
            ), impact=proposal_impact(db, p))
            for p in db.scalars(select(Proposal).order_by(Proposal.created_at.desc()))
        ],
        "versions": [
            fields(v, "id scheme_id version approved_by created_at rule") for v in db.scalars(select(RuleVersion))
        ],
        "audit": [
            fields(a, "id actor_id action target_id created_at")
            for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(100))
        ],
    }


class SourceInput(StrictInput):
    id: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    scheme_id: str
    url: str = Field(max_length=1000)


@app.post(PREFIX + "/admin/sources")
def save_source(body: SourceInput, u=Depends(admin), db: SqlSession = Depends(get_db)):
    from urllib.parse import urlparse
    from .monitor import ALLOWED

    parsed = urlparse(body.url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.fragment
        or parsed.path.lower().endswith(".pdf")
    ):
        raise HTTPException(422, "Only verified allowlisted official HTTPS sources are accepted")
    if not db.get(Scheme, body.scheme_id):
        raise HTTPException(404, "Scheme not found")
    source = db.get(Source, body.id)
    if source and source.url.startswith("fixture://"):
        raise HTTPException(409, "Fictional fixture sources cannot be replaced")
    if source and source.scheme_id != body.scheme_id:
        raise HTTPException(409, "Existing source belongs to a different scheme")
    if source:
        source.url = body.url
    else:
        db.add(Source(id=body.id, scheme_id=body.scheme_id, url=body.url))
    audit(db, u, "source_saved", body.id)
    db.commit()
    return {"ok": True}


@app.get(PREFIX + "/admin/snapshots/{snapshot_id}")
def source_snapshot(snapshot_id: str, u=Depends(admin), db: SqlSession = Depends(get_db)):
    s = db.get(Snapshot, snapshot_id)
    if not s:
        raise HTTPException(404, "Snapshot not found")
    return fields(s, "id source_id content_hash text created_at")


@app.post(PREFIX + "/admin/simulate-change")
def simulate(u=Depends(admin), db: SqlSession = Depends(get_db)):
    from .monitor import simulate_change

    p = simulate_change(db)
    audit(db, u, "source_change_simulated", p.id)
    db.commit()
    return {"id": p.id}


class ProposalEdit(StrictInput):
    proposed_rule: dict
    regression_cases: list[dict]


@app.patch(PREFIX + "/admin/proposals/{proposal_id}")
def edit_proposal(proposal_id: str, body: ProposalEdit, u=Depends(admin), db: SqlSession = Depends(get_db)):
    p = db.get(Proposal, proposal_id)
    if not p or p.state != "pending":
        raise HTTPException(409, "Only pending proposals can be edited")
    p.proposed_rule, p.regression_cases = body.proposed_rule, body.regression_cases
    audit(db, u, "proposal_edited", p.id)
    db.commit()
    return {"ok": True}


@app.post(PREFIX + "/admin/proposals/{proposal_id}/{action}")
def publish(proposal_id: str, action: Literal["approve", "reject"], u=Depends(admin), db: SqlSession = Depends(get_db)):
    p = db.scalar(select(Proposal).where(Proposal.id == proposal_id).with_for_update())
    if not p or p.state != "pending":
        raise HTTPException(409, "Proposal is not pending")
    scheme = db.scalar(select(Scheme).where(Scheme.id == p.scheme_id).with_for_update())
    if action == "reject":
        p.state, p.reviewed_by = "rejected", u.id
    else:
        if scheme.metadata_json["mode"] != "DEMO":
            raise HTTPException(
                409,
                "Real-scheme publication is disabled until source completeness and independent review are implemented",
            )
        if scheme.active_version != p.base_version:
            raise HTTPException(409, "Rule version changed; review a fresh proposal")
        try:
            rule = Rule.model_validate(p.proposed_rule)
            if (
                rule.scheme_id != scheme.id
                or rule.version != p.base_version + 1
                or rule.mode != scheme.metadata_json["mode"]
            ):
                raise ValueError("Rule identity/version mismatch")
            if len(p.regression_cases) < 3 or {c["expected"] for c in p.regression_cases} != {
                "LIKELY_ELIGIBLE",
                "NEEDS_EVIDENCE",
                "NOT_ELIGIBLE",
            }:
                raise ValueError("Independent regression cases for all three verdicts required")
            checks = [
                evaluate(rule, c["facts"], date.fromisoformat(c["date"]))["verdict"] == c["expected"]
                for c in p.regression_cases
            ]
            if not all(checks):
                raise ValueError("Regression tests failed")
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(422, f"Publication validation failed: {str(exc)[:250]}")
        db.add(
            RuleVersion(
                id=f"{scheme.id}:{rule.version}",
                scheme_id=scheme.id,
                version=rule.version,
                rule=rule.model_dump(mode="json"),
                approved_by=u.id,
            )
        )
        for key, value in rule.clauses.items():
            db.add(Clause(id=f"{scheme.id}:v{rule.version}:{key}", scheme_id=scheme.id, text=value, language="en"))
        scheme.active_version = rule.version
        p.state, p.reviewed_by, p.validation = (
            "approved",
            u.id,
            {
                "schema": True,
                "clauses_resolved": True,
                "regression_passed": len(checks),
                "regression_total": len(checks),
            },
        )
    audit(db, u, "proposal_" + p.state, p.id)
    db.commit()
    return {"state": p.state, "validation": p.validation}


@app.post(PREFIX + "/admin/monitor")
def run_monitor(u=Depends(admin)):
    from .monitor import monitor_all

    return {"new_proposals": monitor_all()}


@app.post(PREFIX + "/admin/cleanup")
def run_cleanup(u=Depends(admin)):
    return {"removed": cleanup()}


@app.get(PREFIX + "/admin/evaluation")
def evaluation_metrics(u=Depends(admin)):
    from .evaluation import run_evaluation

    return run_evaluation()


@app.post(PREFIX + "/admin/human-labels")
async def import_labels(file: UploadFile = File(...), u=Depends(admin)):
    from .evaluation import golden_cases, run_evaluation
    import csv
    import io

    data = await file.read(100001)
    if len(data) > 100000:
        raise HTTPException(422, "CSV too large")
    try:
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
        valid_ids = {c["id"] for c in golden_cases()}
        if (
            not rows
            or len({r["id"] for r in rows}) != len(rows)
            or any(
                r["id"] not in valid_ids or r["verdict"] not in ("LIKELY_ELIGIBLE", "NEEDS_EVIDENCE", "NOT_ELIGIBLE")
                for r in rows
            )
        ):
            raise ValueError("CSV needs unique known id and valid verdict columns")
    except (ValueError, KeyError, UnicodeError) as exc:
        raise HTTPException(422, str(exc))
    actual = {r["id"]: r["actual"] for r in run_evaluation()["cases"]}
    result = {
        "labeled_cases": len(rows),
        "agreement": sum(actual[r["id"]] == r["verdict"] for r in rows) / len(rows),
        "labels": rows,
    }
    (storage.ROOT / "human-evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
