from pydantic import BaseModel, EmailStr
from typing import Optional, List


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str
    company_name: Optional[str] = "Outreach Agent"

class LoginForm(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: str
    company_name: str
    calendly: str

    class Config:
        from_attributes = True


# ── Settings ──────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    calendly: Optional[str] = None


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: int
    from_role: str
    label: str
    text: str
    ts: int

    class Config:
        from_attributes = True


# ── People ────────────────────────────────────────────────────────────────────

class PersonCreate(BaseModel):
    name: str
    role: Optional[str] = ""
    service: Optional[str] = "B2B consulting services"
    linkedin_url: Optional[str] = ""
    profile_text: Optional[str] = ""
    personalization: Optional[str] = ""
    prospect_score: Optional[int] = 5
    score_reason: Optional[str] = ""
    status: Optional[str] = "active"
    step: Optional[int] = 1
    created: Optional[str] = ""
    last_activity: Optional[str] = "Today"
    first_message: Optional[str] = ""  # used to create the initial message record

class PersonUpdate(BaseModel):
    step: Optional[int] = None
    status: Optional[str] = None
    prospect_score: Optional[int] = None
    score_reason: Optional[str] = None
    intent: Optional[str] = None
    next_action: Optional[str] = None
    last_activity: Optional[str] = None

class PersonOut(BaseModel):
    id: int
    name: str
    role: str
    service: str
    linkedin_url: str
    personalization: str
    prospect_score: int
    score_reason: str
    status: str
    step: int
    intent: str
    next_action: str
    created: str
    last_activity: str
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True


# ── AI ────────────────────────────────────────────────────────────────────────

class AICreatePersonRequest(BaseModel):
    linkedin_url: str
    profile_text: Optional[str] = ""

class AICreatePersonResponse(BaseModel):
    name: str
    role: str
    service: str
    personalization: str
    prospect_score: int
    score_reason: str
    step1_message: str

class AIHandleReplyRequest(BaseModel):
    person_id: int
    reply_text: str

class AIHandleReplyResponse(BaseModel):
    what_they_mean: str
    conversation_state: str
    why_this_state: str
    score: int
    intent: str
    next_action: str
    reply: str
    short_output: str

class AIRefineReplyRequest(BaseModel):
    person_id: int
    feedback: str  # What the user doesn't like and what they want changed
