"""Explicit setup; no hardcoded accounts or automatic seed at API startup."""

import argparse
import getpass
from sqlalchemy import select
from .db import SessionLocal
from .models import Campus, User, Building, Location, Endpoint, Threshold
from .security import passwords
from .config import settings
from .schemas import Credentials, ThresholdConfig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Campus Administrator")
    parser.add_argument("--campus", default="Demo Campus")
    parser.add_argument("--demo-locations", action="store_true")
    args = parser.parse_args()
    password = getpass.getpass("Administrator password (10+ characters): ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords differ")
    credentials = Credentials(email=args.email, password=password)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == credentials.email)):
            raise SystemExit("Email already exists; bootstrap will not modify existing accounts")
        campus = Campus(name=args.campus, timezone=settings.campus_timezone)
        db.add(campus)
        db.flush()
        db.add(
            User(
                name=args.name,
                email=credentials.email,
                password_hash=passwords.hash(credentials.password),
                role="admin",
                campus_id=campus.id,
            )
        )
        db.add(Threshold(campus_id=campus.id, version=1, config=ThresholdConfig().model_dump()))
        db.add(
            Endpoint(
                campus_id=campus.id,
                name="Campus HTTP Test Server",
                base_url=settings.measurement_base_url,
                scope="campus",
                operator_healthy=False,
            )
        )
        if args.demo_locations:
            for bname, lnames in [
                ("Library", ["Reading Area", "Computer Lab"]),
                ("Engineering Block", ["Lecture Hall", "Lab 1"]),
                ("Student Center", ["Cafeteria"]),
            ]:
                building = Building(campus_id=campus.id, name=bname)
                db.add(building)
                db.flush()
                for lname in lnames:
                    db.add(
                        Location(
                            building_id=building.id,
                            name=lname,
                            description="DEMO configuration: replace with actual campus locations",
                        )
                    )
        db.commit()
        print("Created campus", campus.id, "and administrator", credentials.email)
        print(
            "No fabricated measurements were seeded. Confirm endpoint health after checking server capacity."
        )


if __name__ == "__main__":
    main()
