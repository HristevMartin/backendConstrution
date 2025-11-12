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
    "Heating & Cooling", "Flooring", "Cleaning", "Bricklaying", "Removals", "Handyman",
    "Mechanic",
]


SYSTEM_PROMPT = (
    "You are JOB Hub AI Agent helping homeowners find tradespeople for their job.\n\n"
    
    "SUPPORTED TRADES:\n"
    "Plumbing, Electrical, Carpentry, Roofing, Painting, Gardening, Heating & Cooling, Flooring, Cleaning, Bricklaying, Removals, Handyman, Mechanic\n\n"
    
    "CORE WORKFLOW:\n"  
    "1. User mentions ANY specific trade (e.g., 'electrician', 'plumber', 'carpenter', 'cleaner', 'painter', etc.) → IMMEDIATELY call search_traders for that trade\n"
    "   - DO NOT ask clarifying questions - just search!\n"
    "   - Phrases like 'find me a [trade]', 'I need a [trade]', 'show me [trade]' are ALL direct requests\n"
    "2. User asks for 'any traders', 'registered traders', 'what's available', 'show me something' → show sample of available trades:\n"
    "   - Call search_traders multiple times for different popular trades (Electrical, Plumbing, Bricklaying, Handyman, Carpentry)\n"
    "   - Use limit=2 for each search\n"
    "   - ONLY show traders actually returned by the search tool\n"
    "   - If ALL searches return 0 results, acknowledge NO traders are registered\n"
    "   - DO NOT invent or make up trader names\n"
    "3. If search returns 0 results for specific trade:\n"
    "   - First attempt: Ask if user wants to expand radius\n"
    "   - Second attempt (expanded radius) with 0 results: STOP searching and explain:\n"
    "     'Unfortunately, no [trade] are currently registered on JobHub in your area (within [X]km of [postcode]).\n\n"
    "     You can:\n"
    "     • Try a related trade (e.g., handyman for carpentry work)\n"
    "     • Check back in a few days as we onboard new professionals\n"
    "     • See what other trades are available\n\n"
    "     Would you like me to show you a sample of available traders?'\n"
    "   - If user says yes → search multiple trades (Electrical, Plumbing, Bricklaying, Handyman, Carpentry)\n"
    "   - If ALL searches return 0 results, respond: 'I've searched for multiple trades but there are currently no tradespeople registered in your area. Please check back soon as we onboard new professionals daily.'\n"
    "4. If user asks 'compare' or 'which is best' → provide comparison using existing suggestions\n"
    "5. If user says 'notify [name]' → call notify_trader\n"
    "6. For TRULY general questions (not mentioning any trade) → politely redirect: 'I specialize in finding tradespeople. What type of work do you need?'\n\n"
    
    "SEARCH BEHAVIOR:\n"
    "• Default radius: 15km\n"
    "• If user asks to expand: try 30km\n"
    "• If 30km also returns 0 results for specific trade: STOP and acknowledge unavailable\n"
    "• NEVER search more than twice for the same trade\n"
    "• Track search attempts to avoid loops\n"
    "• When user asks for 'any traders' or 'sample' → search 4-5 different trades with limit=2 each\n"
    "• ONLY present traders actually returned by search_traders tool\n\n"
    
    "DETECTING 'SHOW SAMPLE TRADERS' REQUESTS:\n"
    "User phrases that mean 'show me some available traders':\n"
    "• 'any traders', 'registered traders', 'available traders'\n"
    "• 'what traders are available', 'who is available', 'what do you have'\n"
    "• 'give me any trader', 'show me something', 'show me options'\n"
    "• 'are there any traders', 'who's registered'\n"
    "When you detect these phrases:\n"
    "1. Call search_traders for Electrical (limit 2)\n"
    "2. Call search_traders for Plumbing (limit 2)\n"
    "3. Call search_traders for Bricklaying (limit 2)\n"
    "4. Call search_traders for Handyman (limit 2)\n"
    "5. Call search_traders for Carpentry (limit 2)\n"
    "6. Wait for tool results - DO NOT make up traders\n"
    "7. If tool returns items → present them in formatted list\n"
    "8. If ALL tools return 0 items → tell user no traders are registered\n"
    "CRITICAL: NEVER invent trader names, experiences, or locations\n\n"
    
    "ALTERNATIVE SUGGESTIONS:\n"
    "When no carpenters available, suggest:\n"
    "• Handyman (can do basic carpentry)\n"
    "• General builder\n\n"
    "When no electricians available, suggest:\n"
    "• Handyman (for simple electrical work)\n\n"
    "When no plumbers available, suggest:\n"
    "• Handyman\n"
    "• General builder\n\n"
    "When no bricklayers available, suggest:\n"
    "• General builder\n"
    "• Handyman (for minor brick repairs)\n\n"
    
    "RESPONSE STYLE:\n"
    "• Keep responses under 100 words\n"
    "• Use British English\n"
    "• Be direct and helpful\n"
    "• Don't ask repetitive questions\n"
    "• When clearly no results exist, acknowledge it honestly\n"
    "• NEVER make up or invent trader information\n\n"
    
    "FORMATTING SEARCH RESULTS:\n"
    "When showing traders, format EXACTLY like this:\n\n"
    "Here are [number] traders available near you:\n\n"
    "1. [Name] - [X] years experience, [Trade], [Location] (same area)\n"
    "2. [Name] - [X] years experience, [Trade], [Location] ([distance] km away)\n\n"
    "To get in touch with any of these traders, click the 'Notify via Email' button below their profile.\n\n"
    "FORMATTING RULES:\n"
    "• ONLY use trader data from search_traders tool results\n"
    "• NO trailing dashes after location\n"
    "• NO 'Verified: Yes' field (UI shows verification badges)\n"
    "• Include the trade type when showing mixed trades\n"
    "• Use 'same area' for 0km distance, otherwise show 'X km away'\n"
    "• Keep it clean and simple\n"
    "• NEVER invent trader names or details\n\n"
    
    "CRITICAL RULES:\n"
    "• When user asks 'any traders' or 'registered traders' → IMMEDIATELY search multiple trades\n"
    "• DO NOT ask 'would you like me to search' - just do it\n"
    "• WAIT for tool results before responding\n"
    "• If ALL searches return 0 results → tell user honestly: 'There are currently no tradespeople registered in your area. Please check back soon.'\n\n"
    
    "TRADE REQUEST EXAMPLES (→ SEARCH IMMEDIATELY):\n"
    "✅ 'find me a cleaner' → search for Cleaning\n"
    "✅ 'I need an electrician' → search for Electrical\n"
    "✅ 'show me plumbers' → search for Plumbing\n"
    "✅ 'any painters nearby' → search for Painting\n"
    "✅ 'do you have carpenters' → search for Carpentry\n"
    "✅ 'looking for a handyman' → search for Handyman\n"
    "✅ 'need a bricklayer' → search for Bricklaying\n\n"
    
    "GENERAL QUESTIONS (→ ASK FOR CLARIFICATION):\n"
    "❌ 'what can you do?' → redirect\n"
    "❌ 'tell me about your service' → redirect\n"
    "❌ 'how does this work?' → redirect\n\n"

    "• NEVER make up trader names like 'John Smith', 'Sarah Johnson', 'Mike Brown', etc.\n"
    "• ONLY present traders actually returned by the search_traders function\n"
    "• If search returns empty list → DO NOT show a numbered list of fake traders\n"
    "• DO NOT keep searching if already searched twice for the same specific trade\n"
    "• DO NOT repeat the same question after acknowledging no results\n"
    "• NEVER add trailing dashes or extra separators\n\n"

    "USER REPETITION / ACKNOWLEDGEMENT HANDLING:\n"
    "• If the user says things like 'you already showed me', 'you just did', 'I’ve seen them', 'thanks', or 'that’s fine' — "
    "do NOT repeat previous search results.\n"
    "• Instead, respond politely, for example:\n"
    "  'Got it! Let me know if you'd like to see tradespeople from a different trade or expand the search area.'\n"
    "• Only show new results if the user explicitly asks for a different trade, new location, or wider radius.\n\n"

    
    "TOOL USAGE:\n"
    "• When user asks for specific trade → use limit from request (usually 5)\n"
    "• When showing sample of multiple trades → use limit=2 per trade search\n"
    "• If postcode missing from context → call get_job_context first\n"
    "• Store search results in session - subsequent searches for SAME trade accumulate results\n"
    "• If trade changes → previous results are cleared automatically\n"
    "• When proposing radius expansion → DO NOT search yet, ask for confirmation first\n"
    "• ALWAYS wait for tool response before presenting traders to user\n"
    "• If tool returns empty 'items' array → acknowledge no traders found\n"
    "• Check context['currentRadius'] and lastSearch to provide consistent responses\n\n"

    "CONTEXT PERSISTENCE:\n"
    "• Once a trade is searched, remember it as the 'current trade' for this conversation\n"
    "• Once a radius is set, remember it as the 'current radius'\n"
    "• If user asks 'expand radius' or 'try wider area', offer specific km (e.g., 30km)\n"
    "• When suggesting radius expansion, say: 'Would you like me to search within 30 km instead?'\n"
    "• Store this as pending confirmation - wait for user's yes/no\n"
    "• After user confirms, execute the expanded search automatically\n"
    "• Always maintain consistency: don't say 'no results' if you're about to show results\n"
    "• If you receive lastSearch context showing 0 results at 15km, and user confirms expansion:\n"
    "  - Execute search at 30km\n"
    "  - If found, say: 'I couldn't find any [trade] within 15 km, but within 30 km I found X:'\n\n"
    
    "TRADE CONSISTENCY:\n"
    "• When user asks for specific trade (e.g., 'electrician'), search ONLY that trade\n"
    "• DO NOT mix multiple trades in same response unless user asked for 'any' or 'sample'\n"
    "• If showing multiple trades (user asked for 'any traders'), clearly label each section\n"
    "• Filter final results to match the current trade before presenting\n\n"
    
    "HANDLING REVIEW QUERIES:\n"
    "When user asks about reviews, ratings, or feedback:\n"
    "• Explain that reviews and ratings are visible AFTER the tradesperson applies to the job\n"
    "• Say: 'Trader reviews and ratings will be visible once they apply to your job. This allows you to see their full profile, ratings, and past customer feedback before deciding.'\n"
    "• If user wants to know reviews NOW, say: 'Reviews are only visible after traders apply to protect their privacy. Once they show interest in your job, you'll see their complete profile with all ratings and feedback.'\n"
    "• Never say you don't have access to reviews - explain the privacy/application flow instead\n"
    "• For general questions → politely redirect: 'I specialize in finding tradespeople. What type of work do you need?'\n\n"
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


def _is_greeting(message: str) -> bool:
    """Check if message is just a greeting"""
    msg = message.strip().lower()
    greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 
                 'good evening', 'greetings', 'howdy', 'yo', 'sup']
    
    # Check if message is ONLY a greeting (possibly with punctuation)
    clean_msg = msg.rstrip('!.?')
    return clean_msg in greetings


def _is_confirmation(message: str) -> tuple:
    """
    Check if message is a confirmation (yes/no).
    Returns: (is_confirmation, is_positive)
    """
    msg = message.strip().lower()
    
    positive = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'alright', 
                'go ahead', 'please', 'do it', 'expand']
    negative = ['no', 'nope', 'nah', 'not', "don't", 'cancel']
    
    # Check for positive confirmation
    for word in positive:
        if word == msg or msg.startswith(word + ' ') or msg.endswith(' ' + word):
            return True, True
    
    # Check for negative confirmation
    for word in negative:
        if word == msg or msg.startswith(word + ' ') or msg.endswith(' ' + word):
            return True, False
    
    return False, False


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

            if _is_greeting(user_msg):
                print(f"[UIchatAgent] Greeting detected: '{user_msg}'")
                # Get job info to personalize greeting
                job = ClientProject.objects(project_id=job_id, is_deleted=False).first()
                job_type = "your job"
                if job:
                    service = job.service_category or (job.additional_data or {}).get("serviceCategory")
                    if service:
                        job_type = f"your {service} job"
                
                return {
                    "ok": True,
                    "turnId": turn_id,
                    "receivedAt": ts_iso,
                    "reply": f"Hello! How can I help with {job_type} today? I can help you find tradespeople, compare options, or answer questions.",
                    "suggestions": [],
                    "nextAction": "AWAIT_USER",
                    "slots": {}
                }, 200

            # ========== INITIALIZE OR LOAD SESSION ==========
            session = _SESSION.get(job_id)
            if not session:
                session = {
                    "slots": {},  # Persistent context: trade, radiusKm, postcode
                    "lastCandidates": [],  # Current search results
                    "messages": [],  # Conversation history
                    "searchAttempts": {},  # Track search attempts to prevent loops
                    "pending": None,  # Pending user confirmation (radius expansion, etc.)
                    "lastSearchParams": None,  # Last successful search parameters
                    "updatedAt": datetime.now(timezone.utc)
                }
                _SESSION[job_id] = session
            # ================================================

            # Build messages with conversation history
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            # Add previous conversation turns (last 10 messages = 5 full turns)
            conversation_history = session.get("messages", [])[-4:]
            messages.extend(conversation_history)

            # Add current user message
            messages.append({
                "role": "user", 
                "content": _build_user_envelope(job_id, user_msg, limit, session)
            })

            # ========== HANDLE PENDING CONFIRMATIONS ==========
            # If user is responding to a pending confirmation (e.g., radius expansion)
            if session.get("pending"):
                pending = session["pending"]
                is_conf, is_positive = _is_confirmation(user_msg)
                
                if is_conf:
                    if pending.get("expect") == "radius_confirm" and is_positive:
                        # User confirmed radius expansion - trigger search immediately
                        print(f"[UIchatAgent] User confirmed radius expansion to {pending.get('newRadius')}km")
                        
                        # Get search parameters from pending state
                        trade = pending.get("trade")
                        new_radius = pending.get("newRadius")
                        postcode = session.get("slots", {}).get("postcode")
                        previous_radius = pending.get("previousRadius", 15)
                        
                        # Clear pending state
                        session["pending"] = None
                        
                        # Execute search directly
                        if trade and postcode and new_radius:
                            tool_json = _tool_search_traders(
                                jobId=job_id,
                                trade=trade,
                                postcode=postcode,
                                radiusKm=new_radius,
                                limit=limit
                            )
                            
                            # Update session with results
                            session["lastCandidates"] = tool_json.get("items", [])
                            session["slots"]["radiusKm"] = new_radius
                            session["lastSearchParams"] = {
                                "trade": trade,
                                "postcode": postcode,
                                "radiusKm": new_radius
                            }
                            session["updatedAt"] = datetime.now(timezone.utc)
                            _SESSION[job_id] = session
                            
                            # Build response
                            count = len(session["lastCandidates"])
                            if count > 0:
                                reply = (f"I couldn't find any {trade.lower()} within {previous_radius} km, "
                                        f"but within {new_radius} km I found {count} {trade.lower()}:")
                            else:
                                reply = (f"Unfortunately, no {trade.lower()} are currently registered "
                                        f"within {new_radius} km of {postcode}. "
                                        f"You might want to try a related trade like Handyman.")
                            
                            # Save conversation
                            session["messages"].append({"role": "user", "content": user_msg})
                            session["messages"].append({"role": "assistant", "content": reply})
                            if len(session["messages"]) > 12:
                                session["messages"] = session["messages"][-12:]
                            
                            return {
                                "ok": True,
                                "turnId": turn_id,
                                "receivedAt": ts_iso,
                                "reply": reply,
                                "suggestions": session["lastCandidates"],
                                "nextAction": "SUGGESTIONS_SHOWN" if count > 0 else "NONE",
                                "slots": {
                                    "trade": trade,
                                    "radiusKm": new_radius
                                }
                            }, 200
                    
                    elif not is_positive:
                        # User declined - clear pending and acknowledge
                        print(f"[UIchatAgent] User declined pending action: {pending.get('expect')}")
                        session["pending"] = None
                        session["updatedAt"] = datetime.now(timezone.utc)
                        _SESSION[job_id] = session
                        
                        reply = "No problem. What else can I help you with?"
                        
                        session["messages"].append({"role": "user", "content": user_msg})
                        session["messages"].append({"role": "assistant", "content": reply})
                        
                        return {
                            "ok": True,
                            "turnId": turn_id,
                            "receivedAt": ts_iso,
                            "reply": reply,
                            "suggestions": session.get("lastCandidates", []),
                            "nextAction": "AWAIT_USER",
                            "slots": {}
                        }, 200
            # ==================================================

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
                    max_tokens=1000,
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
                            
                            # Normalize the search trade to ensure consistency
                            normalized_search_trade = _normalise_trade(search_trade) or search_trade
                            
                            # Detect trade change - if searching for different trade, reset candidates
                            current_trade = session.get("slots", {}).get("trade")
                            normalized_current_trade = _normalise_trade(current_trade) if current_trade else None
                            
                            if normalized_current_trade and normalized_search_trade != normalized_current_trade:
                                print(f"[search_traders] Trade changed from {normalized_current_trade} to {normalized_search_trade} - resetting candidates")
                                session["lastCandidates"] = []
                            
                            tool_json = _tool_search_traders(
                                jobId=args.get("jobId") or job_id,
                                trade=search_trade,
                                postcode=search_postcode,
                                radiusKm=search_radius,
                                limit=args.get("limit") or limit
                            )
                            
                            new_items = tool_json.get("items", [])
                            
                            # Count how many search_traders calls have been made in this turn
                            search_count_this_turn = sum(1 for t in tool_results_accumulated if t.get("name") == "search_traders")
                            
                            if search_count_this_turn == 0:
                                # First search in this turn - replace existing candidates
                                session["lastCandidates"] = new_items
                                
                                # Update persistent context (slots) with NORMALIZED search params
                                session["slots"]["trade"] = normalized_search_trade
                                session["slots"]["radiusKm"] = search_radius
                                session["slots"]["postcode"] = search_postcode
                                
                                # Store last successful search params
                                session["lastSearchParams"] = {
                                    "trade": normalized_search_trade,
                                    "postcode": search_postcode,
                                    "radiusKm": search_radius,
                                    "resultCount": len(new_items)
                                }
                            else:
                                # Subsequent search within same turn - accumulate ONLY if same trade
                                if normalized_search_trade == normalized_current_trade:
                                    existing_ids = {c.get("traderId") for c in session.get("lastCandidates", [])}
                                    unique_new = [item for item in new_items if item.get("traderId") not in existing_ids]
                                    
                                    # Add new unique traders, limit total to 8
                                    current = session.get("lastCandidates", [])
                                    combined = current + unique_new
                                    session["lastCandidates"] = combined[:8]  # Cap at 8 total
                                else:
                                    # Different trade - replace (don't mix)
                                    session["lastCandidates"] = new_items
                                    session["slots"]["trade"] = normalized_search_trade
                                    session["slots"]["radiusKm"] = search_radius
                            
                            session["updatedAt"] = datetime.now(timezone.utc)
                            
                            print(f"[search_traders] Search complete: {len(session['lastCandidates'])} total candidates")
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

                comparison_keywords = ['best', 'compare', 'comparison', 'pick', 'choose', 
                       'recommend', 'better', 'which one', 'who should']
                user_msg_lower = user_msg.lower()
                is_comparison_query = any(kw in user_msg_lower for kw in comparison_keywords)

                # If comparison query and we have candidates, build response in Python
                if is_comparison_query and session.get("lastCandidates"):
                    print("[INFO] Comparison query detected - building response in Python")
                    built_comparison = _build_comparison_text(session["lastCandidates"])
                    if built_comparison:
                        assistant_text = built_comparison
                        print(f"[INFO] Built comparison response: {len(assistant_text)} chars")

                # Check if this is a clarifying question (no new search performed this turn)
                search_performed = any(
                    t.get("name") == "search_traders" 
                    for t in tool_results_accumulated
                )

                if search_performed:
                    # Get suggestions from session
                    raw_suggestions = session.get("lastCandidates") or []
                    current_trade = session.get("slots", {}).get("trade")
                    
                    print(f"[UIchatAgent] Search performed. Raw suggestions: {len(raw_suggestions)}, Current trade: {current_trade}")
                    
                    # Normalize current trade for comparison
                    normalized_current = _normalise_trade(current_trade) if current_trade else None
                    
                    # Check if we need to filter
                    if raw_suggestions and normalized_current:
                        # Normalize all trades in results for comparison
                        trades_in_results = set(_normalise_trade(s.get("trade")) or s.get("trade") for s in raw_suggestions)
                        print(f"[UIchatAgent] Normalized trades in results: {trades_in_results}")
                        print(f"[UIchatAgent] Normalized current trade: {normalized_current}")
                        
                        # If we have multiple trades OR current trade doesn't match any result, filter
                        if len(trades_in_results) > 1 or normalized_current not in trades_in_results:
                            suggestions = _filter_suggestions_by_trade(raw_suggestions, normalized_current)
                            print(f"[UIchatAgent] Filtered {len(raw_suggestions)} candidates to {len(suggestions)} matching {normalized_current}")
                        else:
                            # All same trade and matches current - return all
                            suggestions = raw_suggestions
                            print(f"[UIchatAgent] No filtering needed, returning all {len(suggestions)} suggestions")
                    else:
                        # No filtering needed - return all
                        suggestions = raw_suggestions
                        print(f"[UIchatAgent] No filtering needed (no current trade or no suggestions)")
                    
                    next_action = "SUGGESTIONS_SHOWN" if suggestions else "NONE"
                    
                elif is_comparison_query:
                    # For comparison queries, keep showing the existing filtered suggestions
                    current_trade = session.get("slots", {}).get("trade")
                    raw_suggestions = session.get("lastCandidates") or []
                    
                    if current_trade and raw_suggestions:
                        suggestions = _filter_suggestions_by_trade(raw_suggestions, current_trade)
                    else:
                        suggestions = raw_suggestions
                    
                    next_action = "SUGGESTIONS_SHOWN" if suggestions else "NONE"
                    
                else:
                    # No search performed and not a comparison - clear old results
                    suggestions = []
                    next_action = "NONE"
                    

                # ========== SAVE CONVERSATION TO SESSION ==========
                session["messages"].append({
                    "role": "user",
                    "content": user_msg
                })

                session["messages"].append({
                    "role": "assistant",
                    "content": assistant_text
                })

                # Keep only last 20 messages (10 turns) to prevent token overflow
                if len(session["messages"]) > 12:
                    session["messages"] = session["messages"][-12:]

                session["updatedAt"] = datetime.now(timezone.utc)
                _SESSION[job_id] = session
                # ==================================================

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
         "searchAttempts": {},
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


def _get_alternative_trade(trade: str) -> str:
    """Suggest alternative trade when primary trade has no results"""
    alternatives = {
        "Carpentry": "Handyman or General Builder",
        "Electrical": "Handyman (for simple electrical work)",
        "Plumbing": "Handyman or General Builder",
        "Roofing": "General Builder",
        "Painting": "Decorator or Handyman",
        "Gardening": "Landscaper or Handyman",
        "Heating & Cooling": "HVAC Specialist or General",
        "Flooring": "Handyman or General Builder",
        "Cleaning": "Domestic Cleaner or Cleaning Service",
        "Bricklaying": "General Builder or Handyman",
        "Removals": "Moving Company",
        "Mechanic": "Auto Repair Shop",
    }
    
    return alternatives.get(trade, "Handyman")


def _tool_search_traders(jobId: str, trade: str, postcode: str, radiusKm: float, limit: int):
    """Search traders by trade, postcode, and radius"""
    if not jobId or not trade or not postcode:
        return {"ok": False, "error": "Missing parameters for search_traders"}
    
    # Normalize the trade to match database format
    normalized_trade = _normalise_trade(trade)
    if not normalized_trade:
        normalized_trade = trade
    
    # Get session to track search attempts
    session = _SESSION.get(jobId, {})
    search_attempts = session.get("searchAttempts", {})
    
    # Track this search attempt
    attempt_key = f"{normalized_trade}_{radiusKm}"
    search_attempts[attempt_key] = search_attempts.get(attempt_key, 0) + 1
    session["searchAttempts"] = search_attempts
    _SESSION[jobId] = session
    
    job_pc_norm = _norm_pc(postcode)
    active_after = datetime.utcnow() - timedelta(days=90)
    
    # Pull traders from database
    traders = TraderProject.objects()[:800]
    
    print(f"[search_traders] Original trade: {trade}, Normalized: {normalized_trade}")
    print(f"[search_traders] Searching for trade={normalized_trade}, postcode={postcode}, radius={radiusKm}km, limit={limit}")
    print(f"[search_traders] Search attempt #{search_attempts.get(attempt_key, 0)} for this trade/radius")
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
    
    # Include metadata about the search for AI to use
    return {
        "ok": True, 
        "items": rows[:limit],
        "searchMeta": {
            "trade": normalized_trade,
            "radiusKm": radiusKm,
            "postcode": postcode,
            "totalFound": len(rows),
            "attemptNumber": search_attempts.get(attempt_key, 1),
            "suggestion": _get_alternative_trade(normalized_trade) if len(rows) == 0 else None
        }
    }

# =========================
# Helpers
# =========================


def _build_user_envelope(job_id: str, user_msg: str, limit: int, session: dict = None) -> str:
    """
    Wrap user message with full context for the model.
    Includes current suggestions, search history, and pending confirmations.
    """
    envelope = {
        "jobId": job_id,
        "message": user_msg,
        "limit": limit
    }
    
    # Include persistent context (trade, radius, postcode)
    if session and session.get("slots"):
        slots = session["slots"]
        context = {}
        if slots.get("trade"):
            context["currentTrade"] = slots["trade"]
        if slots.get("radiusKm"):
            context["currentRadius"] = slots["radiusKm"]
        if slots.get("postcode"):
            context["postcode"] = slots["postcode"]
        
        if context:
            envelope["context"] = context
    
    # Include current suggestions for context-aware responses (comparison queries)
    if session and session.get("lastCandidates"):
        candidates = session["lastCandidates"]
        envelope["currentSuggestions"] = [
            {
                "number": idx + 1,
                "name": t.get("name"),
                "traderId": t.get("traderId"),
                "trade": t.get("trade"),
                "experienceYears": t.get("experienceYears"),
                "distanceKm": t.get("distanceKm"),
                "verified": t.get("verified"),
                "badges": t.get("badges", []),
                "city": t.get("city")
            }
            for idx, t in enumerate(candidates[:5])
        ]
    
    # Include last search parameters for consistency
    if session and session.get("lastSearchParams"):
        envelope["lastSearch"] = session["lastSearchParams"]
    
    # Include pending confirmation context (e.g., "waiting for yes/no on radius expansion")
    if session and session.get("pending"):
        pending = session["pending"]
        envelope["pendingConfirmation"] = {
            "type": pending.get("expect"),
            "details": {k: v for k, v in pending.items() if k != "expect"}
        }
    
    # Include search attempts to prevent loops
    if session and session.get("searchAttempts"):
        envelope["searchHistory"] = session["searchAttempts"]
    
    return json.dumps(envelope)


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
        "bricklayer": "Bricklaying", "bricklayers": "Bricklaying", "bricklaying": "Bricklaying",
        "brick laying": "Bricklaying", "brickwork": "Bricklaying", "brick work": "Bricklaying",
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



def _filter_suggestions_by_trade(suggestions: list, target_trade: str) -> list:
    """
    Filter suggestions to only include traders matching target trade.
    Sort by: verified (desc), distanceKm (asc), experienceYears (desc)
    """
    if not suggestions or not target_trade:
        return suggestions
    
    # Normalize target trade for comparison
    normalized_target = _normalise_trade(target_trade) or target_trade
    
    # Filter by trade - match against normalized trade
    filtered = []
    for s in suggestions:
        trader_trade = s.get("trade", "")
        # Normalize the trader's trade as well for consistent comparison
        normalized_trader_trade = _normalise_trade(trader_trade) or trader_trade
        
        if normalized_trader_trade == normalized_target:
            filtered.append(s)
    
    print(f"[_filter_suggestions_by_trade] Target: {target_trade} (normalized: {normalized_target}), Found: {len(filtered)}/{len(suggestions)}")
    
    # Sort: verified first, then by distance, then by experience
    filtered.sort(key=lambda x: (
        not x.get("verified", False),  # False sorts before True, so invert
        x.get("distanceKm", 999),
        -(x.get("experienceYears") or 0)  # Negative for descending
    ))
    
    return filtered


def _build_comparison_text(candidates):
    """Build a comparison response from candidates list"""
    if not candidates or len(candidates) < 1:
        return None
    
    if len(candidates) == 1:
        c = candidates[0]
        return (
            f"I found one electrician: **{c['name']}** with {c.get('experienceYears', 'N/A')} years experience, "
            f"located in {c.get('city', 'N/A')} {c.get('postcode', 'N/A')} (same area). "
            f"{'Verified ✓' if c.get('verified') else 'Not verified'}. "
            f"{', '.join(c.get('badges', []))}. "
            f"Click 'Notify via Email' below to contact them directly."
        )
    
    # For 2+ candidates
    c1, c2 = candidates[0], candidates[1]
    
    response = "Here's a quick comparison:\n\n"
    response += f"**1. {c1['name']}**: {c1.get('experienceYears', 'N/A')} years experience, "
    response += f"{c1.get('city', 'N/A')} {c1.get('postcode', 'N/A')}, "
    response += f"{'Verified ✓' if c1.get('verified') else 'Not verified'}"
    
    if c1.get('badges'):
        response += f", {', '.join(c1['badges'])}"
    
    response += f"\n\n**2. {c2['name']}**: {c2.get('experienceYears', 'N/A')} years experience, "
    response += f"{c2.get('city', 'N/A')} {c2.get('postcode', 'N/A')}, "
    response += f"{'Verified ✓' if c2.get('verified') else 'Not verified'}"
    
    if c2.get('badges'):
        response += f", {', '.join(c2['badges'])}"
    
    # Add comparison insight
    exp1 = c1.get('experienceYears', 0) or 0
    exp2 = c2.get('experienceYears', 0) or 0
    
    if exp1 > exp2:
        response += f"\n\n{c1['name']} has {exp1 - exp2} more {'year' if exp1 - exp2 == 1 else 'years'} of experience."
    elif exp2 > exp1:
        response += f"\n\n{c2['name']} has {exp2 - exp1} more {'year' if exp2 - exp1 == 1 else 'years'} of experience."
    else:
        response += "\n\nBoth have equal experience."
    
    # Check for additional certifications
    c1_badges = set(c1.get('badges', []))
    c2_badges = set(c2.get('badges', []))
    unique_to_c1 = c1_badges - c2_badges
    
    if unique_to_c1:
        response += f" {c1['name']} has additional certifications."
    
    response += " Both are good choices!\n\nClick 'Notify via Email' below any trader to contact them directly."
    
    return response



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
