import os
import json
from typing import Optional
from flask import request
from flask_restful import Resource
from openai import OpenAI, RateLimitError, APIError, APIConnectionError, BadRequestError
from managers.auth import auth
from models.TraderProject import TraderProject
from models.ClientProject import ClientProject
from models.ai_cache import AITraderCache
import hashlib
from datetime import datetime


api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

ALLOWED_CATEGORIES = [
    "Plumbing",
    "Electrical",
    "Carpentry",
    "Roofing",
    "Painting",
    "Gardening",
    "Heating & Cooling",
    "Flooring",
    "Cleaning",
    "Bricklaying",
    "Removals",
    "Handyman",
    "Mechanic",
]

SYSTEM_PROMPT = (
    "You are an assistant that writes concise, clear UK home-services job posts.\n"
    "Output helpful, scannable text in British English: a short title (<=120 chars) "
    "plus 2–5 short paragraphs. Avoid quotes/prices and personal data.\n"
    "If asked to classify service category, you MUST choose exactly one value from the "
    "provided allowed list and return it under 'service_category'."
)

def build_user_prompt(
    brief: str,
    postcode: Optional[str],
    category: Optional[str],
    urgency: Optional[str],
    budget: Optional[str],
) -> str:
    parts = [f"Brief: {brief}"]
    if postcode: parts.append(f"Postcode: {postcode}")
    if category: parts.append(f"Service category (optional, may be empty): {category}")
    if urgency:  parts.append(f"Urgency: {urgency}")
    if budget:   parts.append(f"Budget: {budget}")

    parts.append(
        "Return JSON with keys: title, description"
        + (", service_category" if not category else "")
        + "."
    )
    if not category:
        parts.append(
            f"Allowed service categories: {', '.join(ALLOWED_CATEGORIES)}.\n"
            "Pick the single best service_category only from that list."
        )
    return "\n".join(parts)

def _clean(text: str) -> str:
    return (text or "").strip()

class AIHelper(Resource):
    def post(self):
        try:
            if not api_key:
                return {"error": "AI not configured (missing OPENAI_API_KEY)."}, 503

            payload = request.get_json(force=True) or {}
            print("Received payload:", payload)

            # trivial test
            if payload.get("name"):
                return {"echo": payload["name"]}, 200

            brief = _clean(payload.get("brief", ""))
            if not brief:
                return {"error": "brief is required"}, 400

            postcode = _clean(payload.get("postcode", "")) or None
            category = _clean(payload.get("category", "")) or None
            urgency  = _clean(payload.get("urgency", "")) or None
            budget   = _clean(payload.get("budget", "")) or None

            prompt = build_user_prompt(brief, postcode, category, urgency, budget)
            print("Sending prompt to OpenAI...")

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=700,
                response_format={"type": "json_object"},
                timeout=30,
            )

            content = resp.choices[0].message.content
            print("Received response from OpenAI")

            try:
                data = json.loads(content or "{}")
            except Exception as parse_err:
                print(f"JSON parse error: {parse_err}")
                data = {"title": "Job request", "description": content or ""}

            title = _clean(str(data.get("title", "Job request")))[:120]
            description = _clean(str(data.get("description", "")))

            # Validate/normalize service_category if model returned one (or caller provided one)
            svc = _clean(str(data.get("service_category", ""))) or category or ""
            if svc and svc not in ALLOWED_CATEGORIES:
                # Try a simple normalization fallback
                norm = svc.lower()
                mapping = {c.lower(): c for c in ALLOWED_CATEGORIES}
                svc = mapping.get(norm, "")  # blank if not exact match

            result = {
                "title": title,
                "description": description,
                "service_category": svc or None,
            }
            return result, 200

        except RateLimitError as e:
            print(f"Rate limit error: {e}")
            return {"error": "AI is busy. Please try again shortly."}, 429
        except BadRequestError as e:
            print(f"Bad request error: {e}")
            return {"error": f"Invalid request: {str(e)}"}, 400
        except (APIConnectionError, APIError) as e:
            print(f"API error: {e}")
            return {"error": f"AI service error: {str(e)}"}, 502
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {"error": f"Unexpected error: {str(e)}"}, 500



class AITraderHelper(Resource):
    @auth.login_required
    def post(self):
        try:
            if not api_key:
                return {"error": "AI not configured (missing OPENAI_API_KEY)."}, 503

            user_id = str(auth.current_user().id)
            print('show me the usssss', user_id)
            trader_project = TraderProject.objects(userId=user_id).first()
            if not trader_project:
                return {"error": "Trader profile not found"}, 404

            payload = request.get_json(force=True) or {}
            job_id = payload.get("id")
            if not job_id:
                return {"error": "id (job/project_id) is required"}, 400

            client_project = ClientProject.objects(project_id=job_id, is_deleted=False).first()
            if not client_project:
                return {"error": "Client project not found"}, 404

            # Generate cache key based on trader and job details
            cache_key = self.generate_cache_key(user_id, job_id, trader_project, client_project)
            
            # Check cache first
            cached_result = AITraderCache.objects(key=cache_key).first()
            if cached_result:
                print(f"Cache hit for key: {cache_key}")
                return cached_result.value, 200

            trader_obj, client_obj = self.get_the_trade_and_job_details(trader_project, client_project)

            # Build ONE consolidated prompt
            system = (
                "You help UK tradespeople quickly assess job leads. "
                "Be concise, cautious, and avoid firm quotes. British English. "
                "Return VALID JSON ONLY with the schema below. If information is insufficient, "
                "lower the confidence and widen effort bands.\n\n"
                "IMPORTANT: Use objective, factual language only. Do NOT use first-person phrases "
                "like 'I've notified', 'I recommend', 'I think', etc. Provide direct analysis without "
                "referring to yourself or taking actions.\n\n"
                "Schema keys:\n"
                "- summary: string (1–2 sentences)\n"
                "- fit_score: number (0–1) how suitable this job is for this trader\n"
                "- effort_hours: {min: number, max: number} realistic range\n"
                "- complexity: one of low|medium|high\n"
                "- assumptions: string[] (2–4 bullets)\n"
                "- follow_up: string[] (2–4 clarifying questions)\n"
                "- confidence: number (0–1)\n"
                "- disclaimer: string ('Indicative only. Not a quote.')\n"
            )

            user_msg = (
                "Job:\n" + json.dumps(client_obj, ensure_ascii=False) + "\n\n"
                "Trader:\n" + json.dumps(trader_obj, ensure_ascii=False) + "\n\n"
                "Task: Compare the job with the trader profile and return a JSON object with the keys "
                "listed in the schema. Keep it practical and realistic for UK domestic work. "
                "If the service_category and primaryTrade mismatch, reflect that in a lower fit_score "
                "and in assumptions. Do NOT include personal data or pricing."
            )

            # Call OpenAI
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.4,
                max_tokens=450,
                response_format={"type": "json_object"},
                timeout=30,
            )

            # Parse + harden
            import math
            raw = resp.choices[0].message.content or "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}

            def clamp01(x):
                try:
                    return max(0.0, min(1.0, float(x)))
                except Exception:
                    return 0.5

            result = {
                "jobId": client_project.project_id,
                "traderId": trader_project.userId,
                "summary": (data.get("summary") or "").strip()[:280],
                "fit_score": clamp01(data.get("fit_score")),
                "effort_hours": {
                    "min": max(0, int((data.get("effort_hours") or {}).get("min") or 0)),
                    "max": max(0, int((data.get("effort_hours") or {}).get("max") or 0)),
                },
                "complexity": (data.get("complexity") or "medium").lower() if (data.get("complexity") or "").lower() in ["low","medium","high"] else "medium",
                "assumptions": [str(x).strip() for x in (data.get("assumptions") or [])][:4],
                "follow_up": [str(x).strip() for x in (data.get("follow_up") or [])][:4],
                "confidence": clamp01(data.get("confidence")),
                "disclaimer": (data.get("disclaimer") or "Indicative only. Not a quote.").strip(),
            }

            if result["effort_hours"]["max"] and result["effort_hours"]["min"] > result["effort_hours"]["max"]:
                result["effort_hours"]["min"], result["effort_hours"]["max"] = result["effort_hours"]["max"], result["effort_hours"]["min"]

            # Cache the result for future requests
            try:
                cache_entry = AITraderCache(key=cache_key, value=result)
                cache_entry.save()
                print(f"Cached result for key: {cache_key}")
            except Exception as cache_err:
                print(f"Failed to cache result: {cache_err}")
                # Continue without caching - don't fail the request

            return result, 200

        except RateLimitError as e:
            return {"error": "AI is busy. Please try again shortly."}, 429
        except BadRequestError as e:
            return {"error": f"Invalid request: {str(e)}"}, 400
        except (APIConnectionError, APIError) as e:
            return {"error": f"AI service error: {str(e)}"}, 502
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}, 500

    def get_the_trade_and_job_details(self, trader_project, client_project):
        trader_obj = {
            "primaryTrade": trader_project.primaryTrade,
            "experienceYears": trader_project.experienceYears,
            "certifications": trader_project.certifications,
            "city": trader_project.city,
            "postcode": trader_project.postcode,
            "radiusKm": trader_project.radiusKm,
            "bio": trader_project.bio,
        }
        client_obj = {
            "title": client_project.job_title,
            "description": client_project.job_description,
            "service_category": client_project.service_category or (client_project.additional_data or {}).get("serviceCategory"),
            "postcode": client_project.postcode,
            "budget": client_project.budget,
            "urgency": client_project.urgency,
            "image_count": client_project.image_count,
        }
        return trader_obj, client_obj

    def generate_cache_key(self, user_id, job_id, trader_project, client_project):
        """Generate a cache key based on trader and job details that matter for the AI analysis"""
        # Include key fields that would affect the AI analysis
        cache_data = {
            "user_id": user_id,
            "job_id": job_id,
            "trader": {
                "primaryTrade": trader_project.primaryTrade,
                "experienceYears": trader_project.experienceYears,
                "city": trader_project.city,
                "postcode": trader_project.postcode,
                "radiusKm": trader_project.radiusKm,
            },
            "job": {
                "job_title": client_project.job_title,
                "job_description": client_project.job_description,
                "service_category": client_project.service_category or (client_project.additional_data or {}).get("serviceCategory"),
                "postcode": client_project.postcode,
                "budget": client_project.budget,
                "urgency": client_project.urgency,
                "updated_at": str(client_project.updated_at),  # Include to invalidate cache when job is updated
            }
        }
        
        # Create hash of the cache data
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()
        return f"trader_ai_{cache_hash}"


class AIGeneralChat(Resource):
    def post(self):
        try:
            if not api_key:
                return {"error": "AI not configured (missing OPENAI_API_KEY)."}, 503

            payload = request.get_json(force=True) or {}
            message = _clean(payload.get("message", ""))
            
            if not message:
                return {"error": "message is required"}, 400

            # Comprehensive system prompt based on actual platform features
            system_prompt = (
                "You are a knowledgeable assistant for JobHub, a UK platform that connects homeowners with verified tradespeople using AI technology.\n\n"
                
                "PLATFORM FEATURES YOU CAN EXPLAIN:\n\n"
                
                "FOR HOMEOWNERS:\n"
                "- **COMPLETELY FREE to post jobs** - no hidden fees, no charges, no subscription required\n"
                "- AI Job Assistant helps write better job posts with suggested titles and descriptions\n"
                "- 5-step job posting process: Location → Job Details (with AI assistance) → Photos → Budget & Timeline → Contact Details\n"
                "- **IMPORTANT: Registration happens AFTER creating the job post, not before**\n"
                "- Users describe their job first, then provide contact details at the end of the form\n"
                "- After submitting the job, an account is automatically created using the email provided\n"
                "- Optional photo uploads (up to 5 images) to help tradespeople understand the job\n"
                "- Budget ranges: Under £200, £200-£500, £500+, or custom amounts\n"
                "- Urgency options: ASAP, Within a week, Within a month, Flexible\n"
                "- Contact preferences: Email or Phone\n"
                "- Privacy: Details are only shared with tradespeople who apply to your job\n\n"
                
                "AFTER POSTING A JOB (HOMEOWNERS):\n"
                "- Account is automatically created from job posting form\n"
                "- Immediate access to 'My Projects' dashboard to manage all jobs\n"
                "- **Can use AI chatbot to find and invite tradespeople** (see 'Finding Tradespeople' section below)\n"
                "- Can apply for homeowner verification badge ('Verified Client') - brings trust and more applications\n"
                "- Track job activity dashboard showing: Completed jobs, In Progress, Cancelled, Total Posted\n"
                "- View how many tradespeople have applied to each job\n"
                "- Get email notifications when tradespeople apply\n"
                "- Use in-platform chat to communicate with interested tradespeople (after they apply)\n"
                "- View trader profiles, ratings, reviews, certifications, and portfolio (after they apply)\n"
                "- Review system: Leave star ratings (1-5) and written reviews after job completion\n"
                "- Reviews are verified and tied to completed jobs only\n\n"
                
                "FINDING TRADESPEOPLE (HOMEOWNER FLOW):\n"
                "- **Homeowners CANNOT directly browse or see trader profiles after registering**\n"
                "- Instead, homeowners use the **AI chatbot assistant** to find suitable tradespeople\n"
                "- **How it works:**\n"
                "  1. Homeowner posts a job (e.g., 'I need a plumber to fix a leaking tap')\n"
                "  2. Homeowner asks AI chatbot: 'Find me plumbers near me' or 'Show me electricians for my job'\n"
                "  3. AI chatbot analyses the job requirements and suggests best-matched tradespeople\n"
                "  4. AI shows trader cards with: Name, Trade, Location, Distance, Years of experience, Verification badge\n"
                "  5. Homeowner can click **'Notify Trader'** button on any suggested trader\n"
                "  6. System sends an **email invite** to the tradesperson saying they've been matched to a job\n"
                "  7. Tradesperson receives email, reviews the job, and decides whether to apply\n"
                "  8. If tradesperson applies (FREE), they unlock chat access with the homeowner\n"
                "  9. Once tradesperson applies, homeowner can see their full profile, ratings, reviews, portfolio, and certifications\n"
                "- **Key Point**: Homeowners use AI to find matches, then invite traders via 'Notify Trader' button\n"
                "- **Homeowners do NOT see full trader details until the trader applies**\n\n"
                
                "HOMEOWNER REGISTRATION FLOW:\n"
                "1. User clicks 'Post a Job' on homepage\n"
                "2. Fills out job details (location, description, budget, urgency)\n"
                "3. Adds contact information (name, email, phone)\n"
                "4. Submits the job\n"
                "5. Account is automatically created and activated\n"
                "6. Can immediately manage jobs, use AI chatbot to find tradespeople, and invite them\n"
                "**Note: Users do NOT need to register before posting - registration happens automatically as part of job posting**\n\n"
                
                "HOMEOWNER VERIFICATION PROCESS:\n"
                "- **Optional but highly recommended** (increases applications by 2-3x)\n"
                "- **Completely FREE** for homeowners\n"
                "- **Conducted internally by automated verification system**\n"
                "- System checks:\n"
                "  - Profile completeness and accuracy\n"
                "  - Account activity and job posting history\n"
                "  - Email verification status\n"
                "  - Phone number verification (if provided)\n"
                "  - Job posting patterns and authenticity signals\n"
                "- **Sometimes users may be asked to provide additional evidence** such as:\n"
                "  - Proof of address (utility bill, council tax statement)\n"
                "  - Additional contact verification\n"
                "  - Identity confirmation if system flags unusual activity\n"
                "- Verification typically completes within 24-48 hours\n"
                "- Once verified, homeowners receive a green 'Verified Client' badge\n"
                "- **Both verified and unverified homeowners can post jobs and appear on the platform**\n"
                "- **The verified badge is a trust signal** that shows tradespeople this homeowner has been thoroughly checked\n"
                "- Badge is displayed on all job posts and visible to tradespeople\n"
                "- **Verified homeowners typically receive 2-3x more applications** because tradespeople trust verified accounts more\n"
                "- Badge helps homeowners stand out and attract higher quality tradespeople\n\n"
                
                "FOR TRADESPEOPLE:\n"
                "- 4-step registration: Personal Details → Services & Experience → Location & Service Area → Portfolio & Consent\n"
                "- Can select primary trade and additional services offered\n"
                "- Upload certifications and qualifications (e.g., Gas Safe, City & Guilds, NVQ)\n"
                "- Optional portfolio images to showcase previous work\n"
                "- Set service radius (how far willing to travel for jobs)\n"
                "- Browse jobs dashboard with filters: Category, Location, Distance, Urgency, Budget\n"
                "- See platform stats: Active Jobs, Success Rate (%), Average Response Time\n"
                "- **Receive email notifications** when homeowners invite them to jobs via AI chatbot\n\n"
                
                "TRADESPERSON JOB DISCOVERY:\n"
                "- **Two ways tradespeople discover jobs:**\n"
                "  1. **Browse Jobs Dashboard** - See all available jobs in their area matching their trade\n"
                "  2. **Email Invitations** - Receive emails when homeowners use AI chatbot to invite them to specific jobs\n"
                "- Email invitations say something like: 'You've been matched to a job - [Job Title] in [Location]'\n"
                "- Tradespeople can click the email link to view the job details\n"
                "- **Both verified and unverified tradespeople can browse and apply to jobs**\n\n"
                
                "BEFORE APPLYING (TRADESPEOPLE - FREE):\n"
                "- See job title, description, location (city), budget, urgency, photos\n"
                "- See homeowner's first name only (e.g., 'Ivan', 'Kolio')\n"
                "- See if homeowner has 'Verified Client' badge (trust indicator)\n"
                "- See 'Homeowner's Job Activity' stats (completed, active, cancelled, total jobs)\n"
                "- **AI Job Fit Analysis** (if available) provides:\n"
                "  - Fit Score (0-100%) - how well the job matches their profile\n"
                "  - Effort estimate (e.g., 4-8 hours)\n"
                "  - Complexity rating (Low/Medium/High)\n"
                "  - Key assumptions about the job\n"
                "  - Warning if job is outside their typical trade\n"
                "  - AI confidence score for the analysis\n"
                "- All this information is FREE - traders can browse and analyze jobs without paying\n"
                "- **Tradespeople CANNOT see full homeowner details until they apply**\n\n"
                
                "APPLYING FOR JOBS (TRADESPEOPLE - FREE):\n"
                "- **Applying to jobs is completely FREE** - no payment required\n"
                "- Applying unlocks access to **in-platform chat** with the homeowner\n"
                "- Traders do NOT get homeowner's direct contact details (email/phone) immediately\n"
                "- All communication starts through secure in-platform messaging\n"
                "- **Once trader applies:**\n"
                "  - Homeowner can now see the trader's full profile\n"
                "  - Homeowner can see ratings, reviews, certifications, portfolio images\n"
                "  - Both parties can communicate via in-platform chat\n"
                "- Homeowner can choose to share their contact details later through chat if they wish\n"
                "- Homeowner decides whether to continue using platform chat or share direct contact\n"
                "- Platform encourages keeping communication in-chat for safety and tracking\n\n"
                
                "TRADESPERSON VERIFICATION PROCESS:\n"
                "- **Optional but strongly recommended** for all tradespeople joining the platform\n"
                "- **Conducted internally by automated verification system**\n"
                "- System checks:\n"
                "  - Profile completeness (all required fields filled)\n"
                "  - Uploaded qualifications and certifications (quality and authenticity)\n"
                "  - Trade licenses and insurance documents\n"
                "  - Portfolio images and work history\n"
                "  - Account authenticity signals\n"
                "  - Professional references (if provided)\n"
                "- **Sometimes tradespeople may be asked to provide additional evidence** such as:\n"
                "  - Clearer images of certifications\n"
                "  - Proof of insurance documents\n"
                "  - Additional trade qualifications\n"
                "  - Business registration documents\n"
                "  - Identity verification if system flags concerns\n"
                "  - References from past clients\n"
                "- Verification typically completes within 24-72 hours\n"
                "- Once verified, tradespeople receive verification badges displayed on their profiles\n"
                "- **Both verified and unverified tradespeople can apply for jobs and appear on the platform**\n"
                "- **The verified badge is a trust signal** that shows homeowners this tradesperson has been thoroughly checked\n"
                "- **Verified tradespeople are prioritized by homeowners** and receive more job opportunities\n"
                "- **Verified tradespeople appear first in AI chatbot suggestions** when homeowners search for matches\n"
                "- Badge helps tradespeople stand out, build trust, and win more jobs\n"
                "- System continuously monitors accounts for ongoing compliance\n\n"
                
                "IN-PLATFORM CHAT:\n"
                "- Secure messaging system for homeowners and tradespeople\n"
                "- **Chat unlocks immediately when tradesperson applies to a job (FREE)**\n"
                "- Conversations organized by job/project\n"
                "- Both parties can see chat history\n"
                "- Homeowners see list of Active Jobs and Past Jobs with message counts\n"
                "- Real-time messaging with timestamps\n"
                "- Homeowners control whether to share direct contact details\n"
                "- Platform encourages using chat for safety, tracking, and dispute resolution\n\n"
                
                "REVIEWS & RATINGS:\n"
                "- Star rating system: 1-5 stars\n"
                "- Written reviews with optional comments\n"
                "- Reviews can ONLY be left after job completion\n"
                "- Reviews are verified - tied to actual completed jobs\n"
                "- Reviews show: Star rating, job title, date, homeowner name (verified homeowner indicator if applicable)\n"
                "- Average rating displayed on trader profiles (e.g., 4.0/5)\n"
                "- Review count and quality percentage shown\n"
                "- **Both verified and unverified homeowners can leave reviews after job completion**\n"
                "- **Homeowners can only see trader ratings and reviews AFTER the trader applies**\n"
                "- No fake reviews possible - system tracks job completion\n\n"
                
                "TRADER PROFILES (VIEWABLE BY HOMEOWNERS):\n"
                "- **Homeowners can ONLY see full trader profiles AFTER the trader applies to their job**\n"
                "- **Before trader applies**: Homeowners see limited info (name, trade, location, verification badge) via AI chatbot suggestions\n"
                "- **After trader applies**: Homeowners see full profile:\n"
                "  - Profile photo or initial avatar\n"
                "  - Verification status badge (Verified/Unverified) - serves as a trust indicator\n"
                "  - Primary trade specialization\n"
                "  - Years of experience\n"
                "  - Service location and radius (e.g., 10km)\n"
                "  - Star rating and review count\n"
                "  - Certifications & Qualifications displayed with badges (e.g., 'Gold Card', 'CSCS card')\n"
                "  - Certification images (uploaded proof)\n"
                "  - Portfolio gallery with work photos\n"
                "  - Customer reviews section with verified reviews\n"
                "  - Additional services offered\n"
                "  - Member since date\n"
                "- Contact details note: 'Contact information is private. Use the chat feature to get in touch.'\n\n"
                
                "AI CHATBOT FOR FINDING TRADESPEOPLE:\n"
                "- **Primary way for homeowners to find and invite tradespeople**\n"
                "- Homeowner asks chatbot: 'Find me plumbers' or 'Show me electricians near me'\n"
                "- AI analyses the homeowner's job post and suggests best-matched tradespeople\n"
                "- AI considers: Trade type, location/distance, experience, verification status, ratings\n"
                "- Chatbot shows trader suggestion cards with:\n"
                "  - Trader name and trade\n"
                "  - Location and distance from job\n"
                "  - Years of experience\n"
                "  - Verification badge (if verified) - appears as a trust signal\n"
                "  - **'Notify Trader' button** to send email invitation\n"
                "- Homeowner clicks 'Notify Trader' → System sends email to tradesperson\n"
                "- Tradesperson receives email about job match and can review/apply\n"
                "- **Verified tradespeople are shown first in suggestions** to prioritize trusted professionals\n"
                "- **Homeowners do NOT see ratings, reviews, or full profiles until trader applies**\n\n"
                
                "AI FEATURES:\n"
                "- AI Chat Assistant helps homeowners and tradespeople with platform questions\n"
                "- AI chatbot helps homeowners find and invite suitable tradespeople\n"
                "- AI suggests service categories and improves job post clarity (if user asks for help)\n"
                "- AI matches jobs with suitable tradespeople based on trade, location, and experience\n"
                "- Automated verification system with intelligent checks for both homeowners and tradespeople\n"
                "- AI provides recommendations and improves match suggestions over time\n\n"
                
                "JOB TRACKING & VISIBILITY:\n"
                "- Homeowners see application count per job\n"
                "- Job activity dashboard (completed, in progress, cancelled, total)\n"
                "- Job status indicators (Open, Accepting Applicants, Completed, etc.)\n"
                "- Email notifications for new applications\n"
                "- Ability to edit, delete, or mark jobs complete\n"
                "- Track all conversations in one place\n"
                "- See which tradespeople applied and when\n"
                "- Use AI chatbot to find and invite more tradespeople if needed\n\n"
                
                "PRICING:\n"
                "- Homeowners: 100% FREE forever - post unlimited jobs, use AI chatbot to find and invite traders, message traders (after they apply), compare quotes, hire\n"
                "- Homeowner verification: FREE and optional (automated verification, may request additional evidence)\n"
                "- Tradespeople: 100% FREE to browse jobs, receive email invitations, and apply to jobs\n"
                "- Tradespeople: FREE to apply to jobs - no payment required to unlock chat access with homeowner\n"
                "- Tradesperson verification: FREE and optional (strongly recommended for better visibility)\n"
                "- No subscription fees, no monthly charges, no hidden costs, no application fees\n"
                "- Platform is completely free for both homeowners and tradespeople\n\n"
                
                "CONVERSATION GUIDELINES:\n"
                "1. **Be natural and conversational** - Don't sound robotic or overly formal\n"
                "2. **Stay on topic** - If asked about unrelated topics (sports, weather, politics, etc.), politely redirect:\n"
                "   Example: 'I'm specifically designed to help with JobHub platform questions. Is there anything about finding tradespeople or posting jobs I can help with?'\n"
                "3. **Be accurate about registration flow** - Always explain that homeowners register THROUGH job posting, not separately\n"
                "4. **For off-topic questions**, respond with: 'That's outside my area - I focus on JobHub platform questions. Need help with posting a job or finding tradespeople?'\n"
                "5. **Keep responses clear and helpful** - 2-4 sentences typically, but provide complete answers\n"
                "6. **Use British English** spelling and terminology\n"
                "7. **Be friendly but professional** - Match the user's tone\n\n"
                
                "CRITICAL INSTRUCTIONS:\n"
                "1. **ALWAYS emphasize that JobHub is FREE for both homeowners and tradespeople**\n"
                "2. **Be accurate about application process**: When traders apply (FREE), it unlocks CHAT access AND allows homeowner to see full trader profile (ratings, reviews, portfolio), not direct contact details\n"
                "3. **Correct registration flow**: Homeowners register THROUGH job posting form, not before. Account is created automatically and activated immediately - no verification email step.\n"
                "4. **Explain the correct trader discovery flow**:\n"
                "   - Homeowners CANNOT directly browse trader profiles\n"
                "   - Homeowners use AI chatbot to find matches\n"
                "   - Homeowners click 'Notify Trader' to send email invites\n"
                "   - Tradespeople receive emails and decide whether to apply\n"
                "   - Once trader applies (FREE), homeowner sees full profile with ratings/reviews\n"
                "5. **Explain that homeowners control** whether to share contact details later\n"
                "6. **Emphasize verified badges as trust signals** for both homeowners and tradespeople\n"
                "7. When discussing verification:\n"
                "   - **Both homeowners and tradespeople**: Verification is OPTIONAL\n"
                "   - **Verification is conducted by automated system** (not 'AI verification')\n"
                "   - **Additional evidence**: Users may sometimes be asked to provide extra documentation\n"
                "   - **Both verified and unverified users can fully use the platform**\n"
                "   - **Verified badge is a trust signal** - helps users stand out and builds confidence\n"
                "   - Homeowners: Optional, FREE, gets 'Verified Client' badge, increases applications by 2-3x\n"
                "   - Tradespeople: Optional, FREE, gets verification badge, prioritized in AI chatbot suggestions\n"
                "   - **Verified users are prioritized/preferred** by the other party\n"
                "   - **Always call it 'automated verification' or 'verification system'** - NOT 'AI verification'\n"
                "   - Verification typically completes within 24-72 hours\n"
                "8. Explain reviews are verified and tied to completed jobs only\n"
                "9. **Handle off-topic questions gracefully** - Don't try to answer questions outside JobHub scope\n"
                "10. You MUST NOT:\n"
                "   - Say traders need to pay to apply (applying is FREE)\n"
                "   - Say traders get direct contact details when they apply (they get CHAT access + homeowner sees their profile)\n"
                "   - Say homeowners can browse trader profiles directly (they use AI chatbot)\n"
                "   - Say homeowners can see trader ratings/reviews before trader applies (only after trader applies)\n"
                "   - Say verification is mandatory for anyone (it's optional for both)\n"
                "   - Say only verified users can post jobs or apply (both verified and unverified can fully participate)\n"
                "   - Say 'only verified' or 'only ID-checked' professionals (both verified and unverified can use platform)\n"
                "   - Call it 'AI verification' (use 'automated verification system')\n"
                "   - Say homeowners need to register before posting (they register THROUGH posting)\n"
                "   - Mention verification emails or email confirmation for homeowners\n"
                "   - Provide contact details of specific tradespeople\n"
                "   - Give pricing estimates for jobs or services\n"
                "   - Provide technical trade advice\n"
                "   - List or recommend specific tradespeople by name\n"
                "   - Answer questions unrelated to JobHub (sports, news, general knowledge, etc.)\n\n"
                "11. If asked how to find tradespeople:\n"
                "   - Explain they should post a job first (FREE)\n"
                "   - Then use the AI chatbot to ask for matches (e.g., 'Find me plumbers')\n"
                "   - AI will suggest suitable tradespeople (verified ones shown first)\n"
                "   - Click 'Notify Trader' to send email invitation\n"
                "   - Traders receive email and can choose to apply (FREE)\n"
                "   - Once trader applies, homeowner sees full profile\n\n"
                "12. **For unrelated/off-topic questions**:\n"
                "   - Politely say you're focused on JobHub platform questions\n"
                "   - Offer to help with JobHub-related topics instead\n"
                "   - Example: 'I'm here to help with JobHub questions about finding tradespeople and posting jobs. What can I help you with on the platform?'\n\n"
                "13. **Always be accurate about what traders get when they apply (FREE): CHAT access + homeowner can see their full profile**\n"
                "14. Emphasize platform safety through verified reviews and in-platform communication\n"
                "15. **Sound like a helpful human**, not a script-reading robot\n"
                "16. **Never mention verification emails for homeowners** - accounts are automatically created and activated immediately upon job submission\n"
                "17. **When asked about verification**: Always explain it's optional, conducted by an automated system, and additional evidence may be requested for thoroughness. Emphasize that verification is a trust signal that helps users stand out, not a requirement.\n"
                "18. **Be clear that verification badges are trust indicators** - they help users stand out and are preferred by the other party, but unverified users can still fully participate\n"
                "19. **Always explain the AI chatbot flow correctly**: Homeowners use AI chatbot → AI suggests matches (verified first) → Homeowner clicks 'Notify Trader' → Trader receives email → Trader decides to apply (FREE) → Homeowner sees full profile\n"
                "20. **Emphasize the 'Notify Trader' feature**: It's the primary way homeowners invite tradespeople to jobs via AI chatbot\n"
                "21. **Never say 'only verified' or 'only ID-checked'** - both verified and unverified users can fully use the platform. Verification is optional and serves as a trust signal.\n"
                "\n"
                "22. **You can use the previous messages within the current chat session to maintain context, but you do not retain information beyond this session. If the user asks, explain that you remember messages only within this conversation.**\n"
            )

            raw_history = payload.get("history", [])
            print('in1 raw_history', raw_history)
            history = [
                {"role": h.get("role"), "content": h.get("content")}
                for h in raw_history
                if isinstance(h, dict)
                and h.get("role") in ("user", "assistant")
                and isinstance(h.get("content"), str) and h.get("content").strip()
            ]
            print('in2 history', history)
            messages = [{"role": "system", "content": system_prompt}, *history[-8:], {"role": "user", "content": message}]

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=350,  
                timeout=15,
            )

            response_text = resp.choices[0].message.content.strip()
            
            return {
                "message": response_text,
                "reply": response_text,
                "timestamp": datetime.utcnow().isoformat()
            }, 200
    
        except RateLimitError as e:
            print(f"Rate limit error: {e}")
            return {"error": "Chat is busy. Please try again shortly."}, 429
        except BadRequestError as e:
            print(f"Bad request error: {e}")
            return {"error": f"Invalid request: {str(e)}"}, 400
        except (APIConnectionError, APIError) as e:
            print(f"API error: {e}")
            return {"error": f"AI service error: {str(e)}"}, 502
        except Exception as e:
            print(f"Unexpected chat error: {e}")
            return {"error": "Sorry, I'm having trouble responding right now."}, 500