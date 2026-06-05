from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models, schemas
from auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=schemas.UserOut)
def get_settings(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("", response_model=schemas.UserOut)
def update_settings(
    data: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if data.company_name is not None:
        current_user.company_name = data.company_name
    if data.calendly is not None:
        current_user.calendly = data.calendly
    db.commit()
    db.refresh(current_user)
    return current_user
