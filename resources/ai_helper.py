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

            client_project = ClientProject.objects(project_id=job_id).first()
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
