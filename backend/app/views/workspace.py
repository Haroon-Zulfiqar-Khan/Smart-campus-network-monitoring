from ..viewmodels.workspace import ComplaintUpdateInput
from ..viewmodels.workspace import InternetTestInput
from fastapi import APIRouter, Depends
from ..security import current_user
from ..db import get_db
from ..viewmodels.workspace import WorkspaceViewModel, LocationInput, NoteInput, PolicyInput

viewmodel = WorkspaceViewModel()
router = APIRouter(prefix="/workspace", tags=["Dashboard integration"])


@router.post("/internet-test-sessions", status_code=201)
def internet_test(data: InternetTestInput, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.internet_test(data=data, user=user, db=db)


@router.get("")
def snapshot(user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.snapshot(user=user, db=db)


@router.post("/locations", status_code=201)
def create_location(data: LocationInput, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.create_location(data=data, user=user, db=db)


@router.patch("/locations/{id}")
def edit_location(id: str, data: LocationInput, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.edit_location(id=id, data=data, user=user, db=db)


@router.post("/maintenance-notes", status_code=201)
def maintenance_note(data: NoteInput, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.maintenance_note(data=data, user=user, db=db)


@router.patch("/permissions/{role}")
def policy(role: str, data: PolicyInput, user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.policy(role=role, data=data, user=user, db=db)


@router.get("/staff")
def staff(user=Depends(current_user), db=Depends(get_db)):
    return viewmodel.staff(user=user, db=db)


@router.patch("/complaints/{id}")
def update_complaint(
    id: str, data: ComplaintUpdateInput, user=Depends(current_user), db=Depends(get_db)
):
    return viewmodel.update_complaint(id=id, data=data, user=user, db=db)
