from fastapi import APIRouter, Depends
from .. import schemas as S
from ..security import current_user, bearer
from ..db import get_db
from ..viewmodels.auth import AuthViewModel

viewmodel = AuthViewModel()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/campuses")
def campuses(db=Depends(get_db)):
    return viewmodel.campuses(db=db)


@router.post("/register", status_code=201)
def register(data: S.Register, db=Depends(get_db)):
    return viewmodel.register(data=data, db=db)


@router.post("/login")
def login(data: S.Credentials, db=Depends(get_db)):
    return viewmodel.login(data=data, db=db)


@router.post("/refresh")
def refresh(data: S.Refresh, db=Depends(get_db)):
    return viewmodel.refresh(data=data, db=db)


@router.get("/me")
def me(user=Depends(current_user)):
    return viewmodel.me(user=user)


@router.post("/logout")
def logout(user=Depends(current_user), auth=Depends(bearer), db=Depends(get_db)):
    return viewmodel.logout(user=user, auth=auth.credentials, db=db)
