"""Reset only this application's fictional profiles/accounts; preserve rule history and audit."""

import os
from sqlalchemy import select, delete
from . import storage
from .db import DB, Document, Profile, User, Otp
from .seed import seed_profiles


def reset_demo():
    if os.getenv("FORMFLOW_MODE", "DEMO") != "DEMO" or os.getenv("DEVELOPMENT", "true").lower() != "true":
        raise RuntimeError("Reset is restricted to local DEMO mode")
    with DB() as db:
        if db.scalar(select(Profile).where(Profile.fictional.is_(False))):
            raise RuntimeError("Refusing reset: a non-fictional profile exists")
        for doc in db.scalars(select(Document)):
            storage.delete(doc.id)
        db.execute(delete(User))
        db.execute(delete(Otp))
        db.commit()
    seed_profiles()
    print("Fictional accounts, profiles and uploaded objects reset. Rule versions and minimal audit preserved.")


if __name__ == "__main__":
    reset_demo()
