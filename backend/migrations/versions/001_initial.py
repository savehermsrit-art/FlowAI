"""Initial local schema, relational constraints and clause search index."""

from alembic import op
from app.db import Base

revision = "001"
down_revision = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("CREATE INDEX clauses_fts ON source_clauses USING GIN (to_tsvector('simple', text))")


def downgrade():
    Base.metadata.drop_all(op.get_bind())
