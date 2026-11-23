import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    handle: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[str] = mapped_column(String)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Otp(Base):
    __tablename__ = "otp_challenges"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    handle: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    code_hash: Mapped[str] = mapped_column(String)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String)
    language: Mapped[str] = mapped_column(String, default="en")
    fictional: Mapped[bool] = mapped_column(default=True)
    authorization: Mapped[str] = mapped_column(Text, default="self")


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    accepted: Mapped[bool]
    version: Mapped[str] = mapped_column(String, default="2026-11-v1")
    purpose: Mapped[str] = mapped_column(String, default="local preliminary assessment")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Job(Base):
    __tablename__ = "processing_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String, default="queued")
    error: Mapped[str | None] = mapped_column(String, nullable=True)


class Fact(Base):
    __tablename__ = "facts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String)
    original: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    confidence: Mapped[float]
    page: Mapped[int] = mapped_column(Integer, default=1)
    bbox: Mapped[list] = mapped_column(JSON, default=list)
    method: Mapped[str] = mapped_column(String)
    review: Mapped[str] = mapped_column(String, default="unconfirmed")
    issued_at: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String, nullable=True)


class Confirmation(Base):
    __tablename__ = "fact_confirmations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    fact_id: Mapped[str] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Scheme(Base):
    __tablename__ = "schemes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    active_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("schemes.id"), index=True)
    version: Mapped[int]
    rule: Mapped[dict] = mapped_column(JSON)
    approved_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    results: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("schemes.id"))
    url: Mapped[str] = mapped_column(String)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)


class Clause(Base):
    __tablename__ = "source_clauses"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("schemes.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String)


class Snapshot(Base):
    __tablename__ = "source_snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    content_hash: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Proposal(Base):
    __tablename__ = "change_proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("schemes.id"))
    base_version: Mapped[int]
    old_text: Mapped[str] = mapped_column(Text)
    new_text: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String)
    proposed_rule: Mapped[dict] = mapped_column(JSON)
    regression_cases: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[str] = mapped_column(String, default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    validation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Audit(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/formflow.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def fk_on(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")


DB = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with DB() as db:
        yield db
