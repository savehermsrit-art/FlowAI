from sqlalchemy import select
from .db import DB, Scheme, RuleVersion, Source, Clause, User, Profile
from .demo import SCHEMES, demo_rule
from .rules import Rule


def seed():
    with DB() as db:
        for meta in SCHEMES:
            if db.get(Scheme, meta["id"]):
                continue
            db.add(Scheme(id=meta["id"], metadata_json=meta, active_version=1 if meta["mode"] == "DEMO" else None))
            db.flush()
            if meta["mode"] == "DEMO":
                rule = demo_rule(meta["id"])
                Rule.model_validate(rule)
                db.add(
                    RuleVersion(
                        id=meta["id"] + ":1",
                        scheme_id=meta["id"],
                        version=1,
                        rule=rule,
                        approved_by="synthetic specification",
                    )
                )
                for key, value in rule["clauses"].items():
                    db.add(Clause(id=meta["id"] + ":" + key, scheme_id=meta["id"], text=value, language="en"))
                db.add(Source(id=meta["id"], scheme_id=meta["id"], url="fixture://" + meta["id"]))
            else:
                db.add(Source(id=meta["id"], scheme_id=meta["id"], url=meta["source_url"]))
        db.commit()


def seed_profiles():
    """Example profiles have no implied consent and contain no uploaded evidence."""
    with DB() as db:
        for handle, role, cases in [("demo.citizen", "citizen", "ABC"), ("demo.caregiver", "caregiver", "A")]:
            user = db.scalar(select(User).where(User.handle == handle))
            if user:
                continue
            user = User(handle=handle, role=role)
            db.add(user)
            db.flush()
            for case in cases:
                db.add(
                    Profile(
                        owner_id=user.id,
                        name=f"Fictional profile {case}",
                        language="en",
                        fictional=True,
                        authorization="synthetic caregiver authorization fixture" if role == "caregiver" else "self",
                    )
                )
        db.commit()


if __name__ == "__main__":
    seed()
