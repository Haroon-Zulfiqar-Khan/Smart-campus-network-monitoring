from fastapi import APIRouter, Depends, Query
from ..security import current_user
from ..db import get_db
from ..viewmodels.locations import LocationsViewModel

viewmodel = LocationsViewModel()
router = APIRouter(tags=["Campus locations"])


@router.get("/campus")
def campus(user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.campus(user=user, db=db)


@router.get("/buildings")
def buildings(user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.buildings(user=user, db=db)


@router.get("/locations")
def locations(
    building_id: str | None = None,
    include_inactive: bool = False,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    return viewmodel.locations(
        building_id=building_id,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
        user=user,
        db=db,
    )


@router.get("/locations/{id}")
def location(id: str, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.location(id=id, user=user, db=db)


@router.get("/endpoints")
def endpoints(user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.endpoints(user=user, db=db)
