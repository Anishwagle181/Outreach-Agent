import os
import re
import httpx
import time
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
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.55,
        "max_tokens": 900,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            GROQ_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
            },
            json=body,
        )

    if not r.is_success:
        err = r.json().get("error", {}).get("message", "Groq API error")
        raise HTTPException(status_code=502, detail=err)

    return r.json()["choices"][0]["message"]["content"].strip()


def word_count(s: str) -> int:
    return len(s.strip().split())


def clean_personalization(s: str) -> str:
    s = re.sub(r"^Hey\s+\w+,?\s*", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s+", " ", s)
    return s


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


# ── POST /ai/create-person ────────────────────────────────────────────────────

@router.post("/create-person", response_model=schemas.AICreatePersonResponse)
async def create_person_ai(
    data: schemas.AICreatePersonRequest,
    current_user: models.User = Depends(get_current_user),
):
    fallback_name = slug_name(data.linkedin_url)

    system = """You are an elite LinkedIn personalization writer for a B2B outbound agency.

Return JSON only with these keys:
name, role, service, personalization, prospectScore, scoreReason.

PERSONALIZATION RULES:
- Write ONLY the first personalization paragraph.
- EXACTLY 28-35 words. Target 30 words.
- Start with "I like how".
- One paragraph only.
- The goal is to show you understand their OPERATING PHILOSOPHY, not to compliment.
- Focus on: their worldview, how they think about problems, their strategic assumptions, their operating principles.
- This is about showing you've read between the lines - they see growth/problems differently than most people.
- Avoid: generic compliments, job title observations, achievements, credentials, follower counts.
- Avoid clichés: "connecting professionals", "innovative", "intrigued", "expertise", "passionate about".
- Do NOT sound like AI. Sound like a peer who gets it.
- Do NOT repeat their profile wording.

CHARLIE MORGAN STYLE:
- Show deep understanding of their philosophy in fewer words.
- Example: "I like how you frame scaling as a systems and psychology problem rather than a growth-at-all-costs push. You seem to care more about sustainable growth than vanity metrics."
- Example: "I like how your approach treats workforce transitions as human trust moments rather than just HR process. You seem more interested in dignity than compliance."
- Example: "I like how you frame leadership as creating conditions for clear judgment under pressure, not motivation tactics. That's a rarer perspective."

PROSPECT SCORING:
Give prospectScore from 1-10 based on likelihood they'd hire for B2B LinkedIn lead generation.
8-10 = sells B2B services, has growth/pipeline challenges, founder/CEO level.
5-7 = sells B2B, unclear if growth is priority or if they have budget.
1-4 = poor fit: employee, job seeker, student, consumer product, fully booked with referrals only, or skeptical of lead gen.

If profile text is weak, infer from URL/name. Don't fabricate specific claims."""

    user_prompt = f"""LinkedIn URL: {data.linkedin_url}
Fallback name from URL: {fallback_name}
Profile text:
{data.profile_text or "(No profile text pasted. Infer only from URL if possible.)"}"""

    import json
    raw = await call_groq(system, user_prompt, json_mode=True)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {}

    name = (parsed.get("name") or fallback_name or "LinkedIn Person").strip()
    first = name.split()[0]

    personalization = clean_personalization(
        parsed.get("personalization") or
        "I like how your work seems focused on solving business growth as a system rather than relying on random tactics. That practical, operator-led thinking stood out to me."
    )
    if not (28 <= word_count(personalization) <= 35):
        personalization = "I like how your work seems focused on solving growth as a system rather than relying on random tactics. That practical, operator-led way of thinking stood out to me."

    step1 = f"""Hey {first}, {personalization}

Are you taking on more clients at the moment?
Might have something relevant for you :)"""

    return schemas.AICreatePersonResponse(
        name=name,
        role=parsed.get("role") or "",
        service=parsed.get("service") or "B2B consulting services",
        personalization=personalization,
        prospect_score=max(1, min(10, int(parsed.get("prospectScore") or 5))),
        score_reason=parsed.get("scoreReason") or "Initial fit based on profile.",
        step1_message=step1,
    )


# ── POST /ai/handle-reply ─────────────────────────────────────────────────────

@router.post("/handle-reply", response_model=schemas.AIHandleReplyResponse)
async def handle_reply(
    data: schemas.AIHandleReplyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    person = db.query(models.Person).filter(
        models.Person.id == data.person_id,
        models.Person.user_id == current_user.id,
    ).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    calendly = current_user.calendly or CALENDLY_LINK

    system = f"""You are an elite LinkedIn outbound sales strategist.

Your sole objective is to determine the highest-probability next message based on the prospect's buying intent.

You are NOT a copywriter. You are a sales decision engine.

---

PRIMARY GOAL

Maximize positive conversations. Not meetings. Not replies. Not persuasion.

Your goal is to move the conversation forward appropriately based on the prospect's intent.

Sometimes that means asking a question. Sometimes that means addressing a concern. Sometimes that means disqualifying. Sometimes that means booking a call.

Never force movement. Only take the next logical step.

---

CORE PRINCIPLES

1. Never argue. If the prospect believes something, accept their reality.
2. Never defend the offer. Defensiveness lowers trust.
3. Never chase. Neediness kills deals.
4. Never force a call. Calls are earned.
5. Match intent. The reply must feel like the natural continuation of the conversation.
6. Respect resistance. Resistance is information, not something to overcome.
7. Curiosity is stronger than persuasion.
8. The prospect should feel understood, not handled.
9. If someone is not a fit, acknowledge it.
10. Every response should sound like a business owner, never like a salesperson.

---

THINKING PROCESS

Step 1: Identify what the prospect is actually communicating.
Ignore the literal words. Determine the real meaning.

Step 2: Classify buying intent into exactly one category.

A) Closed — Strong resistance, no desire to continue.
B) Soft Objection — Mild resistance, conversation still possible.
C) Curious — Actively engaging, wants information.
D) Interested — Positive buying signals.
E) Ready — Clearly wants next steps.

Step 3: Determine objective based on intent.

Closed: Exit gracefully.
Soft Objection: Reduce friction.
Curious: Continue conversation.
Interested: Increase clarity.
Ready: Move toward a call.

Step 4: Write the message.

Requirements: Natural, Direct, Calm, Professional, Human.

Avoid: Sales language, Manipulation, Pressure, Hype, Excess enthusiasm.

---

LENGTH RULES

Closed: 10-30 words
Soft Objection: 20-40 words
Curious: 30-60 words
Interested: 20-50 words
Ready: 10-30 words

---

FORBIDDEN PHRASES

Do not use:
- "I completely understand"
- "No worries"
- "I'd love to"
- "Just checking in"
- "Following up"
- "Let's hop on a call"
- "Can I pick your brain?"
- "Quick question"
- "Circle back"
- "Touch base"

Avoid all obvious sales clichés.

---

QUALITY CHECK

Before finalizing:

1. Does this feel like a business owner wrote it?
2. Am I trying to persuade them? If yes, rewrite.
3. Am I forcing a call? If yes, rewrite.
4. Does the reply match their actual intent? If not, rewrite.
5. Would a highly skilled outbound operator send this? If not, rewrite.

---

OUTPUT FORMAT

Return JSON only with:
- whatTheyMean: What they're really saying (1-2 sentences)
- intentCategory: Closed | Soft Objection | Curious | Interested | Ready
- leadScore: X/10
- objective: One sentence
- reply: The message only (respecting length rules)

Use intentCategory (not intent).
Calendly link (use only if Ready intent): {calendly}
"""

    conversation_text = "\n\n".join(
        f"{m.from_role}: {m.text}" for m in person.messages
    )

    user_prompt = f"""Prospect: {person.name}
Role: {person.role}
Service: {person.service}
Current score: {person.prospect_score}/10
Calendly link only if ready to book: {calendly}

Conversation so far:
{conversation_text}

Prospect:
{data.reply_text}

Write the best natural reply for this exact situation."""

    import json
    import re as _re

    raw = await call_groq(system, user_prompt, json_mode=True)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {
            "whatTheyMean": "They need a natural follow-up based on their reply.",
            "score": person.prospect_score,
            "intent": "curious",
            "nextAction": "continue_conversation",
            "reply": raw,
        }

    # Normalize new field names to old ones for compatibility
    if "leadScore" in parsed and "score" not in parsed:
        parsed["score"] = parsed["leadScore"]
    if "intentCategory" in parsed and "intent" not in parsed:
        # Map Charlie Morgan categories to internal intent names
        intent_map = {
            "Closed": "bad_fit",
            "Soft Objection": "soft_objection",
            "Curious": "curious",
            "Interested": "curious",
            "Ready": "ready_to_book",
        }
        parsed["intent"] = intent_map.get(parsed["intentCategory"], "curious")
    if "objective" in parsed and "whyThisState" not in parsed:
        parsed["whyThisState"] = parsed["objective"]

    # Hard rejection override
    hard_rejection = bool(_re.search(
        r"(not\s+(trying|looking|interested)|don'?t\s+(need|want)|no\s+(need|thanks|thank you)|all\s+set|already\s+(sorted|covered|good)|not\s+a\s+priority|not\s+right\s+now|no\s+thanks|thanks\s+but)",
        data.reply_text, _re.IGNORECASE
    ))
    if hard_rejection:
        parsed["whatTheyMean"] = "They are clearly not looking to add clients or explore acquisition help right now."
        parsed["conversationState"] = "Dead"
        parsed["whyThisState"] = "They gave a direct rejection with no curiosity or buying signal."
        parsed["intent"] = "bad_fit"
        parsed["nextAction"] = "end_conversation"
        parsed["score"] = 2
        parsed["reply"] = "Makes sense, thanks for letting me know. Appreciate the quick reply."

    ai_reply: str = (parsed.get("reply") or "").strip()
    score = max(1, min(10, int(parsed.get("score") or person.prospect_score or 5)))
    intent = parsed.get("intent") or "curious"
    next_action = parsed.get("nextAction") or "continue_conversation"

    clear_booking = bool(_re.search(
        r"(book|schedule|call|chat|talk|meeting|send.*link|send.*calendar|calendly|time works|availability|speak|connect|yes.*call|open.*call|when.*free|let's.*talk)",
        data.reply_text, _re.IGNORECASE
    ))

    # Hard rejection override - END FAST
    hard_rejection = bool(_re.search(
        r"(not\s+(trying|looking|interested|adding|seeking)|don'?t\s+(need|want)|no\s+(need|thanks|thank you)|all\s+set|already\s+(sorted|covered|good)|not\s+a\s+priority|not\s+right\s+now|no\s+thanks|thanks\s+but|appreciate.*but|pass|nope)",
        data.reply_text, _re.IGNORECASE
    ))
    if hard_rejection:
        parsed["whatTheyMean"] = "They're not interested in exploring this right now."
        parsed["conversationState"] = "Dead"
        parsed["whyThisState"] = "Clear signal to respect their time and move on."
        parsed["intent"] = "bad_fit"
        parsed["nextAction"] = "end_conversation"
        parsed["score"] = 1
        parsed["reply"] = "Makes sense, thanks for letting me know."

    # Force calendly link when closing but missing it
    if (next_action == "close" or intent == "ready_to_book") and not _re.search(r"cal\.com|calendly|grab a time", ai_reply, _re.IGNORECASE):
        ai_reply = f"""Perfect.

Grab a slot here:
{calendly}

Looking forward to the conversation."""

    # Strip calendly from non-booking replies
    if not clear_booking and _re.search(r"cal\.com|grab a time|book a time|calendar|calendly", ai_reply, _re.IGNORECASE):
        # They're not asking for a call yet, so don't push calendly
        ai_reply = """Fair point. Most teams handling this themselves spend months on the outreach side.

What we handle is the consistency and follow-up across conversations—so your pipeline stays full without the time burn.

Worth exploring?"""

    # Enforce word count caps for non-closing messages
    wc = word_count(ai_reply)
    if next_action not in ["close", "end_conversation"] and wc > 50:
        # Too long - truncate to tighter version
        sentences = [s.strip() for s in ai_reply.split('.') if s.strip()]
        if len(sentences) > 2:
            ai_reply = '. '.join(sentences[:2]) + '.'
    
    # Trim dead conversation replies to max 20 words
    if next_action == "end_conversation":
        if word_count(ai_reply) > 20:
            ai_reply = "Makes sense, thanks for letting me know."

    state = parsed.get("conversationState") or (
        "Dead" if next_action == "end_conversation" else
        "Closing" if next_action == "close" else
        "Qualified" if score >= 8 else
        "Curious" if score >= 5 else "Weak"
    )
    why_state = parsed.get("whyThisState") or (
        "There is no clear buying signal, so the safest move is to end politely." if state == "Dead" else
        "They are showing enough intent to move toward a call." if state == "Closing" else
        "There is enough interest to keep moving toward a call." if state == "Qualified" else
        "They are open enough to continue, but still need qualifying." if state == "Curious" else
        "There is low signal, so avoid pushing."
    )

    short_output = f"""Conversation state:
{state}

What they're really saying:
{parsed.get("whatTheyMean") or "They need a natural follow-up."}

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


# ── POST /ai/refine-reply ────────────────────────────────────────────────────

@router.post("/refine-reply", response_model=schemas.AIHandleReplyResponse)
async def refine_reply(
    data: schemas.AIRefineReplyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Regenerate the AI reply based on user feedback."""
    person = db.query(models.Person).filter(
        models.Person.id == data.person_id,
        models.Person.user_id == current_user.id,
    ).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    calendly = current_user.calendly or CALENDLY_LINK

    system = f"""You are an elite LinkedIn outbound sales strategist.

The user gave you feedback on your previous reply. Regenerate the reply using their feedback and the Charlie Morgan framework.

Your sole objective is to determine the highest-probability next message based on the prospect's buying intent.

You are NOT a copywriter. You are a sales decision engine.

---

PRIMARY GOAL

Maximize positive conversations. Not meetings. Not replies. Not persuasion.

Your goal is to move the conversation forward appropriately based on the prospect's intent.

Sometimes that means asking a question. Sometimes that means addressing a concern. Sometimes that means disqualifying. Sometimes that means booking a call.

Never force movement. Only take the next logical step.

---

CORE PRINCIPLES

1. Never argue. If the prospect believes something, accept their reality.
2. Never defend the offer. Defensiveness lowers trust.
3. Never chase. Neediness kills deals.
4. Never force a call. Calls are earned.
5. Match intent. The reply must feel like the natural continuation of the conversation.
6. Respect resistance. Resistance is information, not something to overcome.
7. Curiosity is stronger than persuasion.
8. The prospect should feel understood, not handled.
9. If someone is not a fit, acknowledge it.
10. Every response should sound like a business owner, never like a salesperson.

---

LENGTH RULES

Closed: 10-30 words
Soft Objection: 20-40 words
Curious: 30-60 words
Interested: 20-50 words
Ready: 10-30 words

---

FORBIDDEN PHRASES

Do not use: "I completely understand", "No worries", "I'd love to", "Just checking in", "Following up", "Let's hop on a call", "Can I pick your brain?", "Quick question", "Circle back", "Touch base"

---

QUALITY CHECK

1. Does this feel like a business owner wrote it?
2. Am I trying to persuade them? If yes, rewrite.
3. Am I forcing a call? If yes, rewrite.
4. Does the reply match their actual intent? If not, rewrite.
5. Would a highly skilled outbound operator send this? If not, rewrite.

---

OUTPUT FORMAT

Return JSON only with:
- whatTheyMean: What they're really saying (1-2 sentences)
- intentCategory: Closed | Soft Objection | Curious | Interested | Ready
- leadScore: X/10
- objective: One sentence
- reply: The message only (respecting length rules)

Calendly link (use only if Ready intent): {calendly}
"""

    conversation_text = "\n\n".join(
        f"{m.from_role}: {m.text}" for m in person.messages
    )

    user_prompt = f"""Prospect: {person.name}
Role: {person.role}
Service: {person.service}
Current score: {person.prospect_score}/10
Calendly link only if ready to book: {calendly}

Conversation so far:
{conversation_text}

User feedback on the previous reply:
{data.feedback}

Please regenerate the reply taking this feedback into account. Keep the same conversation context."""

    import json
    import re as _re

    raw = await call_groq(system, user_prompt, json_mode=True)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {
            "whatTheyMean": "They need a refined follow-up based on user feedback.",
            "score": person.prospect_score,
            "intent": "curious",
            "nextAction": "continue_conversation",
            "reply": raw,
        }

    # Normalize new field names to old ones for compatibility
    if "leadScore" in parsed and "score" not in parsed:
        parsed["score"] = parsed["leadScore"]
    if "intentCategory" in parsed and "intent" not in parsed:
        # Map Charlie Morgan categories to internal intent names
        intent_map = {
            "Closed": "bad_fit",
            "Soft Objection": "soft_objection",
            "Curious": "curious",
            "Interested": "curious",
            "Ready": "ready_to_book",
        }
        parsed["intent"] = intent_map.get(parsed["intentCategory"], "curious")
    if "objective" in parsed and "whyThisState" not in parsed:
        parsed["whyThisState"] = parsed["objective"]

    ai_reply: str = (parsed.get("reply") or "").strip()
    score = max(1, min(10, int(parsed.get("score") or person.prospect_score or 5)))
    intent = parsed.get("intent") or "curious"
    next_action = parsed.get("nextAction") or "continue_conversation"

    clear_booking = bool(_re.search(
        r"(book|schedule|call|chat|talk|meeting|send.*link|send.*calendar|calendly|time works|availability|speak|connect|yes.*call|open.*call|when.*free|let's.*talk)",
        person.messages[-1].text if person.messages else "", _re.IGNORECASE
    ))

    # Force calendly link when closing but missing it
    if (next_action == "close" or intent == "ready_to_book") and not _re.search(r"cal\.com|calendly|grab a time", ai_reply, _re.IGNORECASE):
        ai_reply = f"""Perfect.

Grab a slot here:
{calendly}

Looking forward to the conversation."""

    # Strip calendly from non-booking replies
    if not clear_booking and _re.search(r"cal\.com|grab a time|book a time|calendar|calendly", ai_reply, _re.IGNORECASE):
        ai_reply = """Fair point. Most teams handling this themselves spend months on the outreach side.

What we handle is the consistency and follow-up across conversations—so your pipeline stays full without the time burn.

Worth exploring?"""

    # Enforce word count caps for non-closing messages
    wc = word_count(ai_reply)
    if next_action not in ["close", "end_conversation"] and wc > 50:
        sentences = [s.strip() for s in ai_reply.split('.') if s.strip()]
        if len(sentences) > 2:
            ai_reply = '. '.join(sentences[:2]) + '.'
    
    # Trim dead conversation replies to max 20 words
    if next_action == "end_conversation":
        if word_count(ai_reply) > 20:
            ai_reply = "Makes sense, thanks for letting me know."

    state = parsed.get("conversationState") or (
        "Dead" if next_action == "end_conversation" else
        "Closing" if next_action == "close" else
        "Qualified" if score >= 8 else
        "Curious" if score >= 5 else "Weak"
    )
    why_state = parsed.get("whyThisState") or (
        "There is no clear buying signal, so the safest move is to end politely." if state == "Dead" else
        "They are showing enough intent to move toward a call." if state == "Closing" else
        "There is enough interest to keep moving toward a call." if state == "Qualified" else
        "They are open enough to continue, but still need qualifying." if state == "Curious" else
        "There is low signal, so avoid pushing."
    )

    short_output = f"""Conversation state:
{state}

What they're really saying:
{parsed.get("whatTheyMean") or "They need a refined follow-up."}

Why:
{why_state}

Lead score:
{score}/10

Refined reply:
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
