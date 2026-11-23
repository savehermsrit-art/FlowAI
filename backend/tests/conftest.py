import os
import tempfile
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="formflow-tests-"))
os.environ["DATABASE_URL"] = "sqlite:///" + (TEST_ROOT / "test.db").as_posix()
os.environ["DATA_DIR"] = str(TEST_ROOT)
os.environ["DEVELOPMENT"] = "true"
os.environ.pop("REDIS_URL", None)
os.environ.pop("MINIO_ENDPOINT", None)

from app.db import Base, engine
from app.main import app, rates
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    rates.clear()
    with TestClient(app, headers={"X-FormFlow": "1"}) as c:
        yield c


def login(client, handle="synthetic-user", role="citizen"):
    from app.main import admin_key

    response = client.post(
        "/api/v1/auth/request-otp",
        json={"handle": handle, "role": role, "admin_access": admin_key() if role == "admin" else ""},
    )
    assert response.status_code == 200, response.text
    challenge = response.json()
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def citizen(client):
    login(client)
    return client
