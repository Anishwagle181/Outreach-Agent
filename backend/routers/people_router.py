from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
import models, schemas
from auth import get_current_user

router = APIRouter(prefix="/people", tags=["people"])


def today_label():
    return date.today().strftime("%d %b")


@router.get("", response_model=list[schemas.PersonOut])
def list_people(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Person)
        .filter(
            models.Person.user_id == current_user.id,
            models.Person.status != "archived",
        )
        .order_by(models.Person.id.desc())
        .all()
    )


@router.post("", response_model=schemas.PersonOut)
def create_person(
    data: schemas.PersonCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    person = models.Person(
        user_id=current_user.id,
        name=data.name,
        role=data.role or "",
        service=data.service or "B2B consulting services",
        linkedin_url=data.linkedin_url or "",
        profile_text=data.profile_text or "",
        personalization=data.personalization or "",
        prospect_score=data.prospect_score or 5,
        score_reason=data.score_reason or "",
        status=data.status or "active",
        step=data.step or 1,
        created=data.created or today_label(),
        last_activity=data.last_activity or "Today",
    )
    db.add(person)
    db.flush()  # get person.id before commit

    # Create the initial step-1 message if provided
    if data.first_message:
        import time
        msg = models.Message(
            person_id=person.id,
            from_role="you",
            label="Step 1 · Connection / first message",
            text=data.first_message,
            ts=int(time.time() * 1000),
        )
        db.add(msg)

    db.commit()
    db.refresh(person)
    return person


@router.get("/{person_id}", response_model=schemas.PersonOut)
def get_person(
    person_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    person = db.query(models.Person).filter(
        models.Person.id == person_id,
        models.Person.user_id == current_user.id,
    ).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.patch("/{person_id}", response_model=schemas.PersonOut)
def update_person(
    person_id: int,
    data: schemas.PersonUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    person = db.query(models.Person).filter(
        models.Person.id == person_id,
        models.Person.user_id == current_user.id,
    ).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(person, field, value)

    db.commit()
    db.refresh(person)
    return person


@router.delete("/{person_id}")
def delete_person(
    person_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    person = db.query(models.Person).filter(
        models.Person.id == person_id,
        models.Person.user_id == current_user.id,
    ).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    db.delete(person)
    db.commit()
    return {"ok": True}


@router.post("/{person_id}/messages", response_model=schemas.MessageOut)
def add_message(
    person_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    import time
    person = db.query(models.Person).filter(
        models.Person.id == person_id,
        models.Person.user_id == current_user.id,
    ).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    msg = models.Message(
        person_id=person_id,
        from_role=data.get("from_role", "you"),
        label=data.get("label", ""),
        text=data.get("text", ""),
        ts=data.get("ts", int(time.time() * 1000)),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
