from flask_restful import Resource
from flask import request
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from openai import OpenAI, RateLimitError, APIError, APIConnectionError, BadRequestError

# Models
from models.ClientProject import ClientProject
from models.TraderProject import TraderProject

# Import distance calculation from recommendation engine
from services.recommendation_engine import ProjectRecommendationEngine

# OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Initialize recommendation engine for distance calculations
_recommendation_engine = ProjectRecommendationEngine()

# Simple in-memory per-job session (OK for MVP; swap to Redis later)
_SESSION = {}  

ALLOWED_CATEGORIES = [
    "Plumbing", "Electrical", "Carpentry", "Roofing", "Painting", "Gardening",
    "Heating & Cooling", "Flooring", "Cleaning", "Removals", "Handyman", "Mechanic",
]

SYSTEM_PROMPT = (
    "You are JOB Hub AI Agent for a UK home-services marketplace.\n"
    "Objectives:\n"
    "(1) When the user mentions a specific trade name (e.g., 'plumber', 'electrician', 'carpenter', 'mechanic'), "
    "whether as a question ('are there any plumbers?') or statement ('I need a plumber'), "
    "IMMEDIATELY call search_traders with that trade - do NOT ask for confirmation or clarification.\n"
    "(2) If the user provides ONLY a UK postcode (no other context), call get_job_context first to get the trade, "
    "then search with that trade and the new postcode.\n"
    "(3) If the user's request is VAGUE (e.g., 'help with my kitchen', 'need someone', 'fix my house') "
    "and does NOT mention any trade name, DO NOT assume or use job context. Instead, politely ask "
    "what type of tradesperson they need (e.g., 'What kind of work do you need? "
    "For example, plumbing, electrical, carpentry, or something else?').\n"
    "(4) Present ALL available suggestions (ideally 3–5, minimum 2 if available) as a numbered list with ≤20 word rationales.\n"
    "(5) Only notify traders with explicit user consent.\n\n"
    "Rules: British English, concise, never invent trader facts/prices, say 'may apply' not 'will'.\n"
    "When suggesting, include: name, location/postcode, years if present, distance, and a short rationale.\n\n"
    "CRITICAL EXAMPLES:\n"
    "✓ 'are there any plumbers?' → Search for Plumbing immediately\n"
    "✓ 'I need an electrician' → Search for Electrical immediately\n"
    "✓ 'show me mechanics' → Search for Mechanic immediately\n"
    "✗ 'help with my kitchen' → Ask what type of work (no trade mentioned)\n"
    "Always show multiple traders when available."
)

# Tool JSON schemas (function-calling)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_job_context",
            "description": "Fetch job details including trade type, postcode, and radius. ONLY call this when: (1) user provides just a UK postcode with no other context, OR (2) you need the job's postcode/radius for a search. DO NOT call this for vague requests - ask for clarification instead.",
            "parameters": {
                "type": "object",
                "properties": {"jobId": {"type": "string"}},
                "required": ["jobId"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_traders",
            "description": "Deterministic DB search of traders by trade/postcode/radius; returns normalized list",
            "parameters": {
                "type": "object",
                "properties": {
                    "jobId": {"type": "string"},
                    "trade": {"type": "string"},
                    "postcode": {"type": "string"},
                    "radiusKm": {"type": "number"},
                    "limit": {"type": "integer"}
                },
                "required": ["jobId", "trade", "postcode", "radiusKm", "limit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notify_trader",
            "description": "Prepare to notify a trader about the job (no email is sent in this step).",
            "parameters": {
                "type": "object",
                "properties": {
                    "jobId": {"type": "string"},
                    "traderId": {"type": "string"}
                },
                "required": ["jobId", "traderId"]
            }
        }
    }
]


class UIchatAgent(Resource):
    def post(self):
        """
        Tool-calling agent:
          - If trade missing -> model asks.
          - If enough info -> model calls search_traders.
          - We run the DB search and return candidates; model writes final reply.
        Request:
          { "jobId": "...", "message": "free text", "limit": 5 }
        Response (UI-ready):
          {
            "ok": true,
            "turnId": "...",
            "receivedAt": ISO8601,
            "reply": "assistant text",
            "suggestions": [ {traderId, name, trade, city, postcode, distanceKm, experienceYears, verified, badges, image, rationale?} ],
            "nextAction": "NONE" | "SUGGESTIONS_SHOWN" | "AWAIT_NOTIFY_SELECTION",
            "slots": { "trade": "...", "radiusKm": 15 }
          }
        """
        try:
            payload = request.get_json(force=True) or {}
            job_id = (payload.get("jobId") or "").strip()
            user_msg = (payload.get("message") or "").strip()
            limit = int(payload.get("limit") or 5)
            limit = max(1, min(limit, 8))

            if not job_id:
                return {"ok": False, "error": "jobId is required"}, 400
            if not user_msg:
                return {"ok": False, "error": "message is required"}, 400

            turn_id = str(uuid.uuid4())
            ts_iso = datetime.now(timezone.utc).isoformat()

            # Check for low-signal/gibberish input before calling LLM
            if _is_low_signal(user_msg):
                print(f"[UIchatAgent] Low-signal input detected: '{user_msg}'")
                return {
                    "ok": True,
                    "turnId": turn_id,
                    "receivedAt": ts_iso,
                    "reply": "I'm not quite sure what you mean. What kind of tradesperson are you looking for?",
                    "suggestions": [],
                    "nextAction": "AWAIT_USER",
                    "slots": {}
                }, 200

            # Ensure session exists
            session = _SESSION.get(job_id) or {
                "slots": {},
                "lastCandidates": [],
                "updatedAt": datetime.now(timezone.utc)
            }
            _SESSION[job_id] = session

            # Build initial messages (system + user)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_envelope(job_id, user_msg, limit)}
            ]

            # Tool-call loop (max 5 tool interactions per turn)
            tool_results_accumulated = []
            for iteration in range(5):
                print(f"[UIchatAgent] Tool-call iteration {iteration + 1}/5")
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=500,
                    timeout=30,
                )
                msg = resp.choices[0].message

                # If the model requests a tool
                if msg.tool_calls:
                    print(f"[UIchatAgent] AI requested {len(msg.tool_calls)} tool(s): {[tc.function.name for tc in msg.tool_calls]}")
                    
                    # IMPORTANT: Add the assistant's message with tool_calls first
                    messages.append({
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in msg.tool_calls
                        ]
                    })
                    
                    # Now add tool responses
                    for tc in msg.tool_calls:
                        name = tc.function.name
                        args = {}
                        try:
                            args = json.loads(tc.function.arguments or "{}")
                        except Exception:
                            args = {}

                        if name == "get_job_context":
                            tool_json = _tool_get_job_context(job_id)
                        elif name == "search_traders":
                            search_trade = args.get("trade")
                            search_postcode = args.get("postcode")
                            search_radius = args.get("radiusKm")
                            
                            tool_json = _tool_search_traders(
                                jobId=args.get("jobId") or job_id,
                                trade=search_trade,
                                postcode=search_postcode,
                                radiusKm=search_radius,
                                limit=args.get("limit") or limit
                            )
                            # Remember last candidate set for number-based selection UX
                            session["lastCandidates"] = tool_json.get("items", [])
                            session["updatedAt"] = datetime.now(timezone.utc)
                            
                            # Update session slots to reflect the actual search performed (use normalized trade)
                            if search_trade:
                                normalized = _normalise_trade(search_trade)
                                session["slots"]["trade"] = normalized if normalized else search_trade
                            if search_postcode:
                                session["slots"]["postcode"] = search_postcode
                            if search_radius:
                                session["slots"]["radiusKm"] = search_radius
                        elif name == "notify_trader":
                            # We don't actually send here; UI will call your email endpoint.
                            tool_json = {
                                "ok": True,
                                "note": "Prepare notify in UI layer",
                                "jobId": job_id,
                                "traderId": args.get("traderId")
                            }
                        else:
                            tool_json = {"ok": False, "error": f"Unknown tool {name}"}

                        tool_results_accumulated.append({"name": name, "args": args})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": name,
                            "content": json.dumps(tool_json)
                        })
                    # Continue the loop to let the model use the tool results
                    continue

                # No tool calls → final assistant content
                print(f"[UIchatAgent] AI provided final response (no more tool calls)")
                assistant_text = (msg.content or "").strip()
                
                # Check if this is a clarifying question (no new search performed this turn)
                # If no search_traders was called in this turn, clear old suggestions
                search_performed = any(
                    t.get("name") == "search_traders" 
                    for t in tool_results_accumulated
                )
                
                if search_performed:
                    # Show the new search results
                    suggestions = session.get("lastCandidates") or []
                    next_action = "SUGGESTIONS_SHOWN" if suggestions else "NONE"
                else:
                    # No search performed - this is a clarifying question, clear old results
                    suggestions = []
                    next_action = "NONE"

                # Expose minimal slots outward (trade/radiusKm if present)
                slots_out = {}
                slots = session.get("slots") or {}
                if slots.get("trade"):
                    slots_out["trade"] = slots["trade"]
                if slots.get("radiusKm"):
                    slots_out["radiusKm"] = slots["radiusKm"]

                return {
                    "ok": True,
                    "turnId": turn_id,
                    "receivedAt": ts_iso,
                    "reply": assistant_text or "Okay.",
                    "suggestions": suggestions,
                    "nextAction": next_action,
                    "slots": slots_out
                }, 200

            # If loop exits without a final message, check if we have suggestions from tools
            suggestions = session.get("lastCandidates") or []
            slots = session.get("slots") or {}
            
            if suggestions:
                # We have results but AI didn't compose a reply - create one
                trade = slots.get("trade", "tradespeople")
                count = len(suggestions)
                reply = f"I found {count} {trade} {'trader' if count == 1 else 'traders'} for you. Here are the suggestions:"
                
                slots_out = {}
                if slots.get("trade"):
                    slots_out["trade"] = slots["trade"]
                if slots.get("radiusKm"):
                    slots_out["radiusKm"] = slots["radiusKm"]
                
                return {
                    "ok": True,
                    "turnId": turn_id,
                    "receivedAt": ts_iso,
                    "reply": reply,
                    "suggestions": suggestions,
                    "nextAction": "SUGGESTIONS_SHOWN",
                    "slots": slots_out
                }, 200
            
            # No results, return graceful fallback
            return {
                "ok": True,
                "turnId": turn_id,
                "receivedAt": ts_iso,
                "reply": "Let me try that again. You can say 'see suggestions' or tell me the trade (e.g., Electrical).",
                "suggestions": [],
                "nextAction": "NONE",
                "slots": {}
        }, 200

        except RateLimitError:
            return {"ok": False, "error": "AI is busy. Please try again shortly."}, 429
        except BadRequestError as e:
            return {"ok": False, "error": f"Invalid request: {e}"}, 400
        except (APIConnectionError, APIError) as e:
            return {"ok": False, "error": f"AI service error: {e}"}, 502
        except Exception as e:
            print(f"[UIchatAgent][ERROR] {e}")
            return {"ok": False, "error": "Unexpected error"}, 500


# =========================
# Tool implementations
# =========================

def _tool_get_job_context(job_id: str):
    """Fetch job context and populate session slots"""
    job = ClientProject.objects(project_id=job_id, is_deleted=False).first()
    if not job:
        return {"ok": False, "error": "Job not found"}
    
    # Load/prime session slots
    sess = _SESSION.get(job_id) or {
        "slots": {},
        "lastCandidates": [],
        "updatedAt": datetime.now(timezone.utc)
    }
    slots = sess["slots"]
    
    inferred_trade = (job.service_category or (job.additional_data or {}).get("serviceCategory") or "").strip()
    if inferred_trade and "trade" not in slots:
        slots["trade"] = _normalise_trade(inferred_trade) or inferred_trade
    
    radius = _to_float((job.additional_data or {}).get("radiusKm")) or 15.0
    if "radiusKm" not in slots:
        slots["radiusKm"] = float(radius)
    
    _SESSION[job_id] = sess
    
    return {
        "ok": True,
        "job": {
            "jobId": job.project_id,
            "title": (job.job_title or "").strip(),
            "postcode": _norm_pc(job.postcode or ""),
            "trade": slots.get("trade"),
            "radiusKm": slots.get("radiusKm"),
            "budget": (job.budget or None),
            "urgency": (job.urgency or None),
        },
        "slots": slots
    }


def _tool_search_traders(jobId: str, trade: str, postcode: str, radiusKm: float, limit: int):
    """Search traders by trade, postcode, and radius"""
    if not jobId or not trade or not postcode:
        return {"ok": False, "error": "Missing parameters for search_traders"}
    
    # Normalize the trade to match database format (e.g., "plumber" -> "Plumbing")
    normalized_trade = _normalise_trade(trade)
    if not normalized_trade:
        # If normalization fails, try with original trade name
        normalized_trade = trade
    
    job_pc_norm = _norm_pc(postcode)
    active_after = datetime.utcnow() - timedelta(days=90)
    
    # Pull a reasonable slice (tune as needed)
    traders = TraderProject.objects()[:800]
    
    print(f"[search_traders] Original trade: {trade}, Normalized: {normalized_trade}")
    print(f"[search_traders] Searching for trade={normalized_trade}, postcode={postcode}, radius={radiusKm}km, limit={limit}")
    print(f"[search_traders] Total traders in DB: {len(traders)}")

    rows = []
    skipped_reasons = {"no_trade_match": 0, "distance_calc_failed": 0, "outside_radius": 0}
    
    for t in traders:
        try:
            primary = (t.primaryTrade or "").strip()
            others = _parse_services(getattr(t, "otherServices", None))
            
            if not (primary == normalized_trade or normalized_trade in others):
                skipped_reasons["no_trade_match"] += 1
                continue

            t_pc = _norm_pc(getattr(t, "postcode", "") or "")
            d_km = _distance_km(job_pc_norm, t_pc)
            if d_km is None:
                skipped_reasons["distance_calc_failed"] += 1
                continue

            t_rad = _to_float(getattr(t, "radiusKm", None))
            allow_radius = float(radiusKm)
            if isinstance(t_rad, (int, float)) and t_rad > 0:
                allow_radius = min(allow_radius, float(t_rad))
            
            if d_km > allow_radius:
                skipped_reasons["outside_radius"] += 1
                continue

            updated = getattr(t, "updated_at", None)
            is_recent = bool(updated and isinstance(updated, datetime) and updated >= active_after)

            verified = bool(
                (getattr(t, "certificationImages", []) or []) or 
                (getattr(t, "certifications", "") or "").strip()
            )
            
            exp_years = _to_int(getattr(t, "experienceYears", None))
            name = (getattr(t, "name", None) or "Trader").strip()
            email = (getattr(t, "email", None) or "").strip()
            city = (getattr(t, "city", None) or "").strip()
            pc = _norm_pc(getattr(t, "postcode", None) or "")
            img = (getattr(t, "projectImages", []) or [])[:1]

            badges = []
            if verified:
                badges.append("Verified")
            kcert = _extract_key_cert(getattr(t, "certifications", None))
            if kcert:
                badges.append(kcert)

            rows.append({
                "traderId": str(getattr(t, "userId", "")) or str(getattr(t, "id", "")),
                "name": name,
                "email": email,
                "trade": primary or normalized_trade,
                "city": city,
                "postcode": pc,
                "distanceKm": round(float(d_km), 1),
                "experienceYears": exp_years if exp_years is not None else None,
                "verified": verified,
                "badges": badges,
                "image": img[0] if img else None
            })
        except Exception as e:
            print(f"[search_traders] Error processing trader: {e}")
            continue

    # Sort by distance asc
    rows.sort(key=lambda r: r["distanceKm"])
    
    print(f"[search_traders] Found {len(rows)} matching traders")
    print(f"[search_traders] Skipped: {skipped_reasons}")
    print(f"[search_traders] Returning top {min(len(rows), limit)} traders")
    
    return {"ok": True, "items": rows[:limit]}


# =========================
# Helpers
# =========================

def _build_user_envelope(job_id: str, user_msg: str, limit: int) -> str:
    """Wrap user message with light context for the model."""
    return json.dumps({
        "jobId": job_id,
        "message": user_msg,
        "limit": limit
    })


def _normalise_trade(text):
    """Normalize trade names to match allowed categories"""
    if not text:
        return None
    
    txt = str(text).strip().lower()
    mapping = {c.lower(): c for c in ALLOWED_CATEGORIES}
    
    synonyms = {
        "electrician": "Electrical", "electricians": "Electrical", "electrics": "Electrical",
        "plumber": "Plumbing", "plumbers": "Plumbing", "plumbing": "Plumbing", "leak": "Plumbing", "pipe": "Plumbing",
        "carpenter": "Carpentry", "carpenters": "Carpentry", "joiner": "Carpentry",
        "roofer": "Roofing", "roofers": "Roofing", "roof": "Roofing",
        "painter": "Painting", "painters": "Painting", "decorator": "Painting",
        "gardener": "Gardening", "gardeners": "Gardening", "garden": "Gardening",
        "hvac": "Heating & Cooling", "ac": "Heating & Cooling", "boiler": "Heating & Cooling",
        "handyman": "Handyman", "handymen": "Handyman", "odd jobs": "Handyman",
        "floor": "Flooring", "flooring": "Flooring",
        "cleaning": "Cleaning", "cleaner": "Cleaning", "cleaners": "Cleaning",
        "removals": "Removals", "move": "Removals",
        "mechanic": "Mechanic", "mechanics": "Mechanic", "car": "Mechanic",
    }
    
    if txt in mapping:
        return mapping[txt]
    if txt in synonyms:
        return synonyms[txt]
    
    for k, v in synonyms.items():
        if k in txt:
            return v
    
    return mapping.get(txt)


def _parse_services(s):
    """Parse services from JSON string or comma-separated list"""
    if not s:
        return []
    
    s = str(s).strip()
    try:
        arr = json.loads(s)
        if isinstance(arr, list):
            return [str(x).strip() for x in arr if str(x).strip()]
    except Exception:
        pass
    
    return [p.strip() for p in s.split(",") if p.strip()]


def _norm_pc(pc):
    """Normalize postcode format"""
    pc = (pc or "").upper().replace(" ", "")
    if not pc:
        return ""
    return f"{pc[:-3]} {pc[-3:]}" if len(pc) > 3 else pc


def _to_float(x):
    """Safe conversion to float"""
    try:
        return float(str(x).strip())
    except Exception:
        return None


def _to_int(x):
    """Safe conversion to int"""
    try:
        return int(float(str(x).strip()))
    except Exception:
        return None


def _extract_key_cert(cert_text):
    """Extract key certification badges from text"""
    if not cert_text:
        return None
    if "cscs" in str(cert_text).lower():
        return "CSCS card"
    return None


def _distance_km(pc1, pc2):
    """Calculate distance between two postcodes using the recommendation engine"""
    if not pc1 or not pc2:
        return None
    
    try:
        # Use the existing recommendation engine's distance calculation
        distance_miles = _recommendation_engine.get_postcode_distance(pc1, pc2)
        
        # Convert miles to km (1 mile = 1.60934 km)
        distance_km = distance_miles * 1.60934
        
        return distance_km
    except Exception as e:
        print(f"[_distance_km] Error calculating distance between {pc1} and {pc2}: {e}")
        # Fallback: return 0 if same, otherwise None
        return 0.0 if pc1 == pc2 else None


def _is_low_signal(message: str) -> bool:
    """
    Detect if a message is unclear, gibberish, or lacks actionable content.
    Returns True if the message should trigger a clarification response.
    """
    import re
    
    if not message or len(message.strip()) < 3:
        return True
    
    msg = message.strip().lower()
    
    # Check if it's a UK postcode (e.g., "SW1A 1AA", "M1 1AD", "SW20 9NP")
    # UK postcode pattern: 1-2 letters, 1-2 digits, optional letter, space, 1 digit, 2 letters
    postcode_pattern = r'^[a-z]{1,2}\d{1,2}[a-z]?\s?\d[a-z]{2}$'
    if re.match(postcode_pattern, msg):
        return False
    
    # Meaningful keywords that indicate intent
    intent_keywords = [
        'electrician', 'electricians', 'electrical', 'plumber', 'plumbers', 'plumbing', 
        'carpenter', 'carpenters', 'carpentry', 'roofer', 'roofers', 'roofing', 
        'painter', 'painters', 'painting', 'gardener', 'gardeners', 'gardening',
        'heating', 'cooling', 'flooring', 'cleaning', 'removals', 'handyman', 'handymen',
        'mechanic', 'mechanics',
        'suggest', 'suggestion', 'show', 'find', 'search', 'need', 'want', 'looking',
        'notify', 'contact', 'hire', 'quote', 'help', 'radius', 'distance', 'km', 'miles',
        'yes', 'no', 'ok', 'okay', 'thanks', 'thank', 'hi', 'hello', 'hey', 'see',
        'postcode', 'location', 'area', 'near', 'are', 'any', 'there'
    ]
    
    # Check if message contains any meaningful keywords
    has_intent = any(keyword in msg for keyword in intent_keywords)
    if has_intent:
        return False
    
    # Check for repeated patterns (e.g., "dasdasdas", "aaaaaaa")
    # If same 2-3 char sequence repeats 3+ times, it's likely gibberish
    if re.search(r'(.{2,3})\1{2,}', msg):
        return True
    
    # Check if mostly non-alphabetic (>70% non-letters)
    letters = sum(c.isalpha() for c in msg)
    if letters < len(msg) * 0.3:
        return True
    
    # Check if it's just numbers
    if msg.replace(' ', '').isdigit() and len(msg) < 5:
        # Allow numbers like "20" (could be radius), but not long sequences
        return False
    
    # If message has reasonable length and some letters but no clear intent
    if len(msg) > 20 and letters / len(msg) > 0.5:
        # Longer messages with letters but no keywords - let LLM handle
        return False
    
    # Short messages without intent keywords
    if len(msg) < 10:
        return True
    
    return False
