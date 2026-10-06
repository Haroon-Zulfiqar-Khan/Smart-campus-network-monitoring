from fastapi import APIRouter, Depends, Query
from .. import schemas as S
from ..security import admin
from ..db import get_db
from ..viewmodels.admin import AdminViewModel

viewmodel = AdminViewModel()
router = APIRouter(prefix="/admin", tags=["Administration"])


@router.post("/buildings", status_code=201)
def building(data: S.BuildingCreate, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.building(data=data, user=user, db=db)


@router.post("/locations", status_code=201)
def location(data: S.LocationCreate, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.location(data=data, user=user, db=db)


@router.patch("/locations/{id}")
def update_location(id: str, data: S.LocationUpdate, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.update_location(id=id, data=data, user=user, db=db)


@router.get("/users")
def users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(admin),
    db=Depends(get_db),
):
    return viewmodel.users(limit=limit, offset=offset, user=user, db=db)


@router.post("/users", status_code=201)
def create_user(data: S.UserCreate, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.create_user(data=data, user=user, db=db)


@router.patch("/users/{id}")
def update_user(id: str, data: S.UserUpdate, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.update_user(id=id, data=data, user=user, db=db)


@router.get("/thresholds")
def config(user=Depends(admin), db=Depends(get_db)):
    return viewmodel.config(user=user, db=db)


@router.post("/thresholds", status_code=201)
def set_thresholds(data: S.ThresholdConfig, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.set_thresholds(data=data, user=user, db=db)


@router.post("/endpoints", status_code=201)
def endpoint(data: S.EndpointCreate, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.endpoint(data=data, user=user, db=db)


@router.patch("/endpoints/{id}")
def endpoint_update(id: str, data: S.EndpointUpdate, user=Depends(admin), db=Depends(get_db)):
    return viewmodel.endpoint_update(id=id, data=data, user=user, db=db)


@router.get("/audit")
def audit_list(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(admin),
    db=Depends(get_db),
):
    return viewmodel.audit_list(limit=limit, offset=offset, user=user, db=db)
