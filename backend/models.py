from sqlalchemy import Column, Integer, String, Float, ForeignKey, BigInteger, DateTime, func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    company_name = Column(String, default="Outreach Agent")
    calendly = Column(String, default="https://cal.com/nexa-lead-qng40v/15min")
    business_description = Column(String, default="")
    offer = Column(String, default="")
    target_customer = Column(String, default="")
    outreach_style = Column(String, default="")
    personalization_style = Column(String, default="")
    personalization_examples = Column(String, default="")
    objection_style = Column(String, default="")
    step1_script = Column(String, default="")
    step2_script = Column(String, default="")
    step3_script = Column(String, default="")
    step4_script = Column(String, default="")
    onboarding_complete = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    people = relationship("Person", back_populates="owner", cascade="all, delete-orphan")


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="")
    service = Column(String, default="B2B consulting services")
    linkedin_url = Column(String, default="")
    profile_text = Column(String, default="")
    personalization = Column(String, default="")
    prospect_score = Column(Integer, default=5)
    score_reason = Column(String, default="")
    status = Column(String, default="active")  # active | replied | closing | booked | weak | archived
    step = Column(Integer, default=1)
    intent = Column(String, default="")
    next_action = Column(String, default="")
    created = Column(String, default="")
    last_activity = Column(String, default="Today")

    owner = relationship("User", back_populates="people")
    messages = relationship("Message", back_populates="person", cascade="all, delete-orphan", order_by="Message.ts")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    from_role = Column(String, nullable=False)  # you | them | ai
    label = Column(String, default="")
    text = Column(String, nullable=False)
    ts = Column(BigInteger, default=0)

    person = relationship("Person", back_populates="messages")
