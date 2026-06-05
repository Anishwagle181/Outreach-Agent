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
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)

    # If they saved business context, treat onboarding as complete.
    if any(getattr(current_user, f, "") for f in ["business_description", "offer", "target_customer"]):
        current_user.onboarding_complete = 1

    db.commit()
    db.refresh(current_user)
    return current_user
