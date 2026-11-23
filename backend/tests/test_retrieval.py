from sqlalchemy import select
from app.db import DB, Clause, Source
from app.monitor import ingest_snapshot
from app.retrieval import chunks


def test_clause_chunking_and_stable_ids(client):
    assert list(chunks("First clause.\n\nSecond clause.")) == ["First clause.", "Second clause."]
    assert max(map(len, chunks("word " * 1000))) <= 1200
    with DB() as db:
        source = db.get(Source, "demo-silver")
        assert ingest_snapshot(db, source, "First clause.\n\nವಯಸ್ಸು 60 years.") is None
        db.commit()
        before = {c.id for c in db.scalars(select(Clause).where(Clause.scheme_id == source.scheme_id))}
        assert ingest_snapshot(db, source, "First clause.\n\nವಯಸ್ಸು 60 years.") is None
        proposal = ingest_snapshot(db, source, "First clause.\n\nವಯಸ್ಸು 65 years.")
        assert proposal and proposal.state == "pending"
        db.commit()
        after = {c.id for c in db.scalars(select(Clause).where(Clause.scheme_id == source.scheme_id))}
        assert before.issubset(after) and len(after) == len(before) + 1
