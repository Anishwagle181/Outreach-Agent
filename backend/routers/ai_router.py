import os
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_db
import models, schemas
from auth import get_current_user

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
CALENDLY_LINK = os.getenv("CALENDLY_LINK", "https://cal.com/nexa-lead-qng40v/15min")

router = APIRouter(prefix="/ai", tags=["ai"])


async def call_groq(system: str, user: str, json_mode: bool = False) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Groq API key not configured on server")
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.35,
        "max_tokens": 1100,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            GROQ_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"},
            json=body,
        )
    if not r.is_success:
        err = r.json().get("error", {}).get("message", "Groq API error")
        raise HTTPException(status_code=502, detail=err)
    return r.json()["choices"][0]["message"]["content"].strip()


def word_count(s: str) -> int:
    return len((s or "").strip().split())


def clean_personalization(s: str) -> str:
    s = re.sub(r"^Hey\s+\w+,?\s*", "", s or "", flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", " ", s)


def slug_name(url: str) -> str:
    try:
        from urllib.parse import urlparse
        parts = [p for p in urlparse(url).path.split("/") if p]
        last = parts[-1] if parts else ""
        last = re.sub(r"[-_]+", " ", last)
        last = re.sub(r"\d+", "", last).strip()
        return " ".join(w.capitalize() for w in last.split() if w) or "LinkedIn Person"
    except Exception:
        return "LinkedIn Person"


def business_context(user: models.User) -> str:
    return f"""
BUSINESS CONTEXT FOR THIS USER
Company: {user.company_name}
Business description: {user.business_description}
Offer: {user.offer}
Target customer / ICP: {user.target_customer}
How they do outreach: {user.outreach_style}
Personalization style: {user.personalization_style}
Personalization examples: {user.personalization_examples}
Objection handling style: {user.objection_style}
Calendar link: {user.calendly or CALENDLY_LINK}
""".strip()


def step1_template(user: models.User) -> str:
    return user.step1_script or """Hey [Name], [personalization]

Are you taking on more clients at the moment?
Might have something relevant for you :)"""


@router.post("/create-person", response_model=schemas.AICreatePersonResponse)
async def create_person_ai(data: schemas.AICreatePersonRequest, current_user: models.User = Depends(get_current_user)):
    fallback_name = slug_name(data.linkedin_url)
    system = f"""You are an elite LinkedIn personalization writer.

{business_context(current_user)}

Return JSON only with these keys:
name, role, service, personalization, prospectScore, scoreReason.

PERSONALIZATION RULES:
- Write ONLY the first personalization paragraph.
- EXACTLY 28-35 words. Target 30 words.
- Start with "I like how".
- One paragraph only.
- Make it highly specific to the prospect AND relevant to the user's business/offer.
- The goal is to show you understand how the prospect thinks, not to compliment them.
- Focus on operating philosophy, worldview, strategic assumptions, or how they approach their market.
- If this user sells accounting outreach, personalize around accounting/business owners.
- If this user sells SaaS, personalize around SaaS/product/GTM.
- If this user sells agency lead gen, personalize around agencies/client acquisition.
- Do NOT mention titles, years, awards, followers, revenue, credentials, or achievements.
- Do NOT say "I noticed", "impressive", "congratulations", "intrigued", "expertise", or "passionate".
- Do NOT repeat the profile wording directly.

PROSPECT SCORING:
Score based on fit for THIS user's offer and ICP, not generic lead gen.
8-10 = strong ICP and likely has the problem this user solves.
5-7 = possible fit but unclear urgency/budget.
1-4 = poor fit or unlikely buyer.
"""
    user_prompt = f"""LinkedIn URL: {data.linkedin_url}
Fallback name from URL: {fallback_name}
Profile text:
{data.profile_text or "(No profile text pasted. Infer carefully from URL only if possible.)"}
"""
    import json
    try:
        parsed = json.loads(await call_groq(system, user_prompt, json_mode=True))
    except Exception:
        parsed = {}
    name = (parsed.get("name") or fallback_name or "LinkedIn Person").strip()
    first = name.split()[0]
    personalization = clean_personalization(parsed.get("personalization") or "I like how your work seems focused on solving growth as a system rather than relying on random tactics. That practical, operator-led way of thinking stood out to me.")
    if not (28 <= word_count(personalization) <= 35):
        # Ask one repair pass for tighter 30-word personalization.
        repair_system = "Rewrite the personalization into exactly 28-35 words, starting with 'I like how'. Return JSON only: {\"personalization\": \"...\"}"
        try:
            fixed = json.loads(await call_groq(repair_system, personalization, json_mode=True))
            personalization = clean_personalization(fixed.get("personalization") or personalization)
        except Exception:
            pass
    if not (28 <= word_count(personalization) <= 35):
        personalization = "I like how your work seems focused on solving growth as a system rather than relying on random tactics. That practical, operator-led way of thinking stood out to me."

    step1 = step1_template(current_user).replace("[Name]", first).replace("[personalization]", personalization)
    return schemas.AICreatePersonResponse(
        name=name,
        role=parsed.get("role") or "",
        service=parsed.get("service") or "B2B services",
        personalization=personalization,
        prospect_score=max(1, min(10, int(parsed.get("prospectScore") or 5))),
        score_reason=parsed.get("scoreReason") or "Initial fit based on profile and user ICP.",
        step1_message=step1,
    )


def normalize_intent(parsed: dict):
    if "leadScore" in parsed and "score" not in parsed:
        parsed["score"] = parsed["leadScore"]
    if "intentCategory" in parsed and "intent" not in parsed:
        parsed["intent"] = {
            "Closed": "bad_fit", "Soft Objection": "soft_objection", "Curious": "curious",
            "Interested": "interested", "Ready": "ready_to_book"
        }.get(parsed["intentCategory"], "curious")
    if "objective" in parsed and "whyThisState" not in parsed:
        parsed["whyThisState"] = parsed["objective"]
    return parsed


async def reply_engine(person: models.Person, current_user: models.User, latest_text: str, feedback: str = ""):
    calendly = current_user.calendly or CALENDLY_LINK
    system = f"""
You are an elite LinkedIn outbound operator, objection handler, deal reader, and sales strategist.

You are working inside this exact business:

{business_context(current_user)}

Your job is NOT to blindly answer prospects.

Your job is to make the smartest possible next move in the conversation.

Think like:

* a calm agency owner
* a top 1% setter
* a business strategist
* someone who has handled thousands of LinkedIn conversations
* someone who protects trust and only closes when timing is right

PRIMARY OBJECTIVE:

Move qualified prospects toward a call.
Disqualify poor-fit prospects quickly.
Never force a conversation.
Never chase.
Never sound like a salesperson.

=================================================
CORE SALES PRINCIPLE
====================

The goal is NOT to ask the next question.

The goal is to make the highest-value next move.

Before replying determine:

1. What are they really saying?
2. What emotional state are they in?
3. What stage are they in?
4. What is the safest next move?
5. What would a smart business owner say?

=================================================
MOMENTUM RULE
=============

Never move backwards.

Examples:

BAD:
Prospect: "Yes, I'm interested."
Reply: "Are you actively looking to solve this?"

BAD:
Prospect: "Let's talk Monday."
Reply: "Can I ask a few questions first?"

BAD:
Prospect: "Send me your calendar."
Reply: More qualification questions.

GOOD:
Prospect: "I'm interested."
Reply: Move toward a call.

GOOD:
Prospect: "Let's talk Monday."
Reply: Send calendar.

GOOD:
Prospect: "How does it work?"
Reply: Explain briefly then move forward.

Never re-qualify someone who already qualified themselves.

=================================================
CONVERSATION DIAGNOSIS
======================

Classify the prospect into one of:

Dead
Weak
Curious
Qualified
Closing

Dead:

* No interest
* Not looking
* Hard rejection
* Wrong timing
* Wrong fit

Weak:

* Polite response
* Mild engagement
* No real curiosity

Curious:

* Asking questions
* Wants clarification
* Exploring

Qualified:

* Problem exists
* Open to solution
* Relevant fit

Closing:

* Wants next steps
* Wants calendar
* Wants call
* Wants details

=================================================
INTENT CLASSIFICATION
=====================

Classify intent as:

bad_fit
soft_objection
curious
interested
ready_to_book
partnership

Examples:

bad_fit:

* not interested
* already solved
* looking for a job
* wrong audience

soft_objection:

* referrals work fine
* too busy
* not right now
* already have support

curious:

* what do you do?
* how does it work?
* tell me more
* what are you selling?

interested:

* maybe
* possibly
* sounds interesting
* open to hearing more

ready_to_book:

* yes
* let's chat
* send your calendar
* book me in
* available Monday

partnership:

* referrals
* co-marketing
* audience
* promotion
* collaboration
* JV
* strategic relationship

=================================================
OBJECTION HANDLING RULES
========================

Never argue.

Never defend.

Never pressure.

Never try to "overcome" objections.

Understand them first.

A good objection reply:

* agrees with reality
* lowers resistance
* lightly reframes
* moves naturally

A bad objection reply:

* pushes harder
* explains too much
* defends the service
* sounds needy

=================================================
TRUST RULE
==========

Prospects do not buy because they understand the offer.

Prospects buy because:

* they trust you
* they feel understood
* they believe timing is right
* they see relevance

Every reply should do one of:

* build trust
* reduce friction
* create clarity
* move forward

Never reply just to keep the conversation alive.

=================================================
CALL BOOKING RULES
==================

Move to a call when:

* prospect asks for more information
* prospect asks how it works
* prospect expresses interest
* prospect agrees to chat
* prospect asks for next steps
* prospect asks for a link

Do NOT delay the call with unnecessary qualification.

Do NOT ask another question when the prospect is already ready.

=================================================
STYLE
=====

Write like:

* experienced founder
* smart operator
* trusted advisor

NOT:

* sales rep
* SDR
* chatbot

Tone:

* calm
* confident
* concise
* human
* direct

=================================================
FORBIDDEN PHRASES
=================

Never say:

* I completely understand
* No worries
* I'd love to
* Let's hop on a call
* Quick question
* Just checking in
* Touch base
* Following up
* Sounds good
* Totally
* Circle back

=================================================
REPLY LENGTH
============

Dead:
10-20 words

Weak:
20-40 words

Soft objection:
30-60 words

Curious:
30-60 words

Qualified:
40-70 words

Closing:
10-35 words

General rule:

* 2-4 sentences
* Under 60 words
* Under 10 seconds to read

If the reply takes longer than 10 seconds to read, it is too long.

=================================================
QUALITY BAR
===========

The reply should feel like it came from someone who has handled thousands of LinkedIn sales conversations.

It should never:

* feel scripted
* feel automated
* feel desperate
* feel salesy
* feel pushy

It should respond to the actual words used by the prospect.

=================================================
OUTPUT FORMAT
=============

Return JSON only:

{
"whatTheyMean": "What they are really saying beneath the surface in 1-2 sentences.",
"conversationState": "Dead | Weak | Curious | Qualified | Closing",
"whyThisState": "Why this is the correct state.",
"score": 1-10,
"intent": "bad_fit | soft_objection | curious | interested | ready_to_book | partnership",
"nextAction": "end_conversation | continue_conversation | qualify | close",
"reply": "Actual LinkedIn reply only"
}

Calendar link (ONLY when ready_to_book):

{calendly}
"""

    conversation_text = "\n\n".join(f"{m.from_role}: {m.text}" for m in person.messages)
    user_prompt = f"""Prospect: {person.name}
Role: {person.role}
Service: {person.service}
Current score: {person.prospect_score}/10

Conversation so far:
{conversation_text}

Latest prospect reply:
{latest_text}

User feedback if refining:
{feedback}

Write the best natural reply for this exact situation."""
    import json
    try:
        parsed = normalize_intent(json.loads(await call_groq(system, user_prompt, json_mode=True)))
    except Exception as e:
        parsed = {"whatTheyMean": "They need a natural follow-up.", "conversationState": "Curious", "whyThisState": "Not enough signal to close yet.", "score": person.prospect_score or 5, "intent": "curious", "nextAction": "continue_conversation", "reply": "Makes sense. What would need to be true for this to be worth a short conversation?"}

    hard_rejection = bool(re.search(r"(not\s+(trying|looking|interested|adding|seeking)|don'?t\s+(need|want)|no\s+(need|thanks|thank you)|all\s+set|already\s+(sorted|covered|good)|not\s+a\s+priority|not\s+right\s+now|no\s+thanks|thanks\s+but|appreciate.*but|pass|nope)", latest_text, re.I))
    if hard_rejection:
        parsed.update({"whatTheyMean": "They are not interested in exploring this right now.", "conversationState": "Dead", "whyThisState": "Clear rejection with no buying signal.", "score": 1, "intent": "bad_fit", "nextAction": "end_conversation", "reply": "Makes sense, thanks for letting me know."})

    ai_reply = (parsed.get("reply") or "").strip()
    score = max(1, min(10, int(parsed.get("score") or person.prospect_score or 5)))
    intent = parsed.get("intent") or "curious"
    next_action = parsed.get("nextAction") or "continue_conversation"
    clear_booking = bool(re.search(r"(book|schedule|call|chat|talk|meeting|send.*link|send.*calendar|calendly|time works|availability|speak|connect|yes.*call|open.*call|when.*free|let'?s.*talk)", latest_text, re.I))
    if (next_action == "close" or intent == "ready_to_book") and not re.search(r"cal\.com|calendly|grab a time", ai_reply, re.I):
        ai_reply = f"Perfect.\n\nGrab a slot here:\n{calendly}\n\nLooking forward to the conversation."
    if not clear_booking and re.search(r"cal\.com|grab a time|book a time|calendar|calendly", ai_reply, re.I):
        ai_reply = "Makes sense. Before sharing anything, it probably only makes sense if this is actually a priority right now. Are you actively looking to improve this, or just curious?"
    if next_action == "end_conversation" and word_count(ai_reply) > 25:
        ai_reply = "Makes sense, thanks for letting me know."

    state = parsed.get("conversationState") or ("Dead" if next_action == "end_conversation" else "Closing" if next_action == "close" else "Qualified" if score >= 8 else "Curious" if score >= 5 else "Weak")
    why_state = parsed.get("whyThisState") or "Based on their reply and buying intent."
    short_output = f"""Conversation state:
{state}

What they're really saying:
{parsed.get('whatTheyMean') or 'They need a natural follow-up.'}

Why:
{why_state}

Lead score:
{score}/10

Recommended reply:
{ai_reply}"""
    return schemas.AIHandleReplyResponse(
        what_they_mean=parsed.get("whatTheyMean") or "",
        conversation_state=state,
        why_this_state=why_state,
        score=score,
        intent=intent,
        next_action=next_action,
        reply=ai_reply,
        short_output=short_output,
    )


@router.post("/handle-reply", response_model=schemas.AIHandleReplyResponse)
async def handle_reply(data: schemas.AIHandleReplyRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    person = db.query(models.Person).filter(models.Person.id == data.person_id, models.Person.user_id == current_user.id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return await reply_engine(person, current_user, data.reply_text)


@router.post("/refine-reply", response_model=schemas.AIHandleReplyResponse)
async def refine_reply(data: schemas.AIRefineReplyRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    person = db.query(models.Person).filter(models.Person.id == data.person_id, models.Person.user_id == current_user.id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    latest = person.messages[-1].text if person.messages else ""
    return await reply_engine(person, current_user, latest, feedback=data.feedback)
