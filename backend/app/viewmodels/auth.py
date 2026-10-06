from ..errors import DomainError as HTTPException
from sqlalchemy import select, update
from .. import schemas as S
from ..models import User, Campus, LoginSession, now
from ..common import get, serialize, audit
from ..security import passwords, DUMMY_HASH, issue, digest, decode


class AuthViewModel:
    """Orchestrates use cases and prepares state consumed by API Views."""

    @staticmethod
    def campuses(db=None):
        return [serialize(c) for c in db.scalars(select(Campus).order_by(Campus.name)).all()]

    @staticmethod
    def register(data: S.Register, db=None):
        get(db, Campus, data.campus_id)
        if db.scalar(select(User).where(User.email == data.email)):
            raise HTTPException(409, "Email already registered")
        user = User(
            name=data.name,
            email=data.email,
            password_hash=passwords.hash(data.password),
            campus_id=data.campus_id,
            role="student",
        )
        db.add(user)
        db.flush()
        audit(db, user, "user.registered", user)
        return {"user": serialize(user), **issue(db, user)}

    @staticmethod
    def login(data: S.Credentials, db=None):
        user = db.scalar(select(User).where(User.email == data.email))
        valid = passwords.verify(data.password, user.password_hash if user else DUMMY_HASH)
        if not user or not valid or (not user.is_active):
            raise HTTPException(401, "Incorrect credentials")
        audit(db, user, "user.login", user)
        return {"user": serialize(user), **issue(db, user)}

    @staticmethod
    def refresh(data: S.Refresh, db=None):
        session = db.scalar(
            select(LoginSession)
            .where(LoginSession.refresh_hash == digest(data.refresh_token))
            .with_for_update()
        )
        if not session or session.revoked or session.expires_at < now():
            raise HTTPException(401, "Invalid refresh token")
        user = get(db, User, session.user_id)
        if not user.is_active:
            raise HTTPException(401, "Account inactive")
        claimed = db.execute(
            update(LoginSession)
            .where(
                LoginSession.id == session.id,
                LoginSession.revoked.is_(False),
                LoginSession.refresh_hash == digest(data.refresh_token),
            )
            .values(revoked=True)
        )
        if claimed.rowcount != 1:
            raise HTTPException(401, "Refresh token was already consumed")
        return issue(db, user)

    @staticmethod
    def me(user=None):
        return serialize(user)

    @staticmethod
    def logout(user=None, auth=None, db=None):
        session = get(db, LoginSession, decode(auth)["sid"])
        session.revoked = True
        audit(db, user, "user.logout", user)
        return {"message": "Logged out; access and refresh tokens revoked"}
