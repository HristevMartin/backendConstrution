import os
import json
from typing import Optional
from flask import request
from flask_restful import Resource
from openai import OpenAI, RateLimitError, APIError, APIConnectionError, BadRequestError

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
