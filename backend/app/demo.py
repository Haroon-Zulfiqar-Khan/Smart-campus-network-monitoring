"""Opt-in local demo accounts; prints generated passwords once. Never used in production."""

import argparse
import secrets
from sqlalchemy import select
from .config import settings
from .db import SessionLocal
from .models import Campus, User
from .security import passwords


def main():
    if settings.environment == "production":
        raise SystemExit("Demo accounts are disabled in production")
    parser = argparse.ArgumentParser()
    parser.add_argument("--campus-id", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        if not db.get(Campus, args.campus_id):
            raise SystemExit("Campus not found")
        for name, role in [("student", "student"), ("it", "support"), ("manager", "manager")]:
            email = name + "@demo.campus"
            if db.scalar(select(User).where(User.email == email)):
                print("Skipped existing account", email)
                continue
            password = secrets.token_urlsafe(16)
            db.add(
                User(
                    name="Demo " + name,
                    email=email,
                    role=role,
                    campus_id=args.campus_id,
                    password_hash=passwords.hash(password),
                )
            )
            print(email, "role=" + role, "password=" + password)
        db.commit()
        print("Demo accounts only. Replace campus locations before real monitoring.")


if __name__ == "__main__":
    main()
