"""Render entry point: configure, migrate and initialize only an empty database."""

import os
import subprocess
import sys


def prepare_environment(env):
    url = env.get("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            env["DATABASE_URL"] = "postgresql+psycopg://" + url[len(prefix) :]
            break
    external = env.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not external.startswith("https://"):
        raise RuntimeError("RENDER_EXTERNAL_URL must be the public HTTPS Render service URL.")
    env["MEASUREMENT_BASE_URL"] = external + "/probe/measure"


def initialize_campus(db, env):
    from sqlalchemy import select
    from .models import Campus, User, Threshold, Endpoint
    from .schemas import Credentials, ThresholdConfig
    from .security import passwords
    from .config import settings

    # Redeploys never overwrite existing accounts, passwords or campus records.
    if db.scalar(select(Campus.id).limit(1)):
        return False
    email = env.get("INITIAL_ADMIN_EMAIL", "").strip()
    password = env.get("INITIAL_ADMIN_PASSWORD", "")
    try:
        credentials = Credentials(email=email, password=password)
    except ValueError:
        # Pydantic errors can include input values; never print them for secrets.
        raise RuntimeError(
            "Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD (10-128 characters, no surrounding spaces) in Render."
        ) from None
    campus = Campus(
        name=env.get("INITIAL_CAMPUS_NAME", "Mehran University of Engineering and Technology"),
        timezone=settings.campus_timezone,
    )
    db.add(campus)
    db.flush()
    db.add(
        User(
            name="Campus Administrator",
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
    db.commit()
    return True


def main():
    prepare_environment(os.environ)
    # Import after environment normalization, including production validation.
    from .db import SessionLocal

    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    with SessionLocal() as db:
        if initialize_campus(db, os.environ):
            print(
                "Campus and initial administrator created. Add actual campus locations in the dashboard.",
                flush=True,
            )
    # Bootstrap credentials are no longer needed by the serving process.
    os.environ.pop("INITIAL_ADMIN_PASSWORD", None)
    import uvicorn

    uvicorn.run(
        "app.render_app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), workers=1
    )


if __name__ == "__main__":
    main()
