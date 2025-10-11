from datetime import datetime, timedelta
import math
import requests
from collections import defaultdict
from typing import Dict, Tuple, List 



class ProjectRecommendationEngine:
    """
    Handles all project recommendation logic including:
    - Geographic proximity calculations (cached + batched)
    - User preference matching
    - Project categorization and ranking
    """

    def __init__(self, postcode_api_key=None):
        self.postcode_api_key = postcode_api_key
        self.base_postcode_url = "http://api.postcodes.io"
        # Reuse TCP connections across requests
        self._session = requests.Session()
        # Small in-memory cache: { "SW209NP": (lon, lat) }
        self._coords_cache: Dict[str, Tuple[float, float]] = {}

    # -------------------- helpers: coords & distance --------------------

    def _norm_pc(self, postcode: str) -> str:
        """Normalize a postcode to 'SW209NP' (no spaces, uppercase)."""
        return (postcode or "").replace(" ", "").upper()

    def _get_coords_single(self, pc_norm: str) -> Tuple[float, float]:
        """Get (lon, lat) for a single normalized postcode, with cache."""
        if not pc_norm:
            raise ValueError("empty postcode")

        # Cache hit
        if pc_norm in self._coords_cache:
            return self._coords_cache[pc_norm]

        # Fetch & cache
        r = self._session.get(
            f"{self.base_postcode_url}/postcodes/{pc_norm}",
            timeout=1.5
        )
        r.raise_for_status()
        res = r.json()["result"]
        val = (res["longitude"], res["latitude"])
        self._coords_cache[pc_norm] = val
        return val

    def _warm_coords_batch(self, pcs_norm: List[str]) -> None:
        """Batch-prefetch coords for up to 100 postcodes at a time."""
        if not pcs_norm:
            return

        # Postcodes.io supports up to 100 postcodes per batch call
        for i in range(0, len(pcs_norm), 100):
            chunk = pcs_norm[i:i + 100]
            try:
                r = self._session.post(
                    f"{self.base_postcode_url}/postcodes",
                    json={"postcodes": chunk},
                    timeout=1.5
                )
                if r.status_code != 200:
                    continue
                payload = r.json().get("result", [])
                for item in payload:
                    res = item.get("result")
                    pc = (item.get("query") or "").upper()
                    if res and pc:
                        self._coords_cache[pc] = (res["longitude"], res["latitude"])
            except Exception:
                # Non-fatal: per-item lookups will still work
                pass

    @staticmethod
    def _haversine_miles(lon1, lat1, lon2, lat2) -> float:
        """Great-circle distance in miles."""
        R = 3958.7613  # miles
        dlon = math.radians(lon2 - lon1)
        dlat = math.radians(lat2 - lat1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return 2 * R * math.asin(math.sqrt(a))

    # -------------------- public API used elsewhere --------------------

    def get_postcode_distance(self, postcode1, postcode2) -> float:
        """
        Fast distance: cached coords + local Haversine.
        Falls back to a coarse area heuristic; never blocks response.
        """
        try:
            pc1 = self._norm_pc(postcode1)
            pc2 = self._norm_pc(postcode2)
            if not pc1 or not pc2:
                return 999.0
            if pc1 == pc2:
                return 0.0
            lon1, lat1 = self._get_coords_single(pc1)
            lon2, lat2 = self._get_coords_single(pc2)
            return round(self._haversine_miles(lon1, lat1, lon2, lat2), 2)
        except Exception:
            area1 = self._norm_pc(postcode1)[:4]
            area2 = self._norm_pc(postcode2)[:4]
            return 0.0 if (area1 and area1 == area2) else 999.0

    def get_user_recommendations(self, user_postcode, projects_list, user_preferences=None):
        """
        Enrich projects with distance; filter by max radius; categorize & sort.
        """
        defaults = {
            'max_radius_miles': 25,
            'preferred_radius_miles': 10,
        }
        prefs = {**defaults, **(user_preferences or {})}

        # If trader lacks a postcode, skip geo and just return with distance=None
        if not user_postcode:
            enriched = [{**p, "distance_miles": None} for p in projects_list]
            # Keep your existing output shape
            return self._sort_and_limit_recommendations({"immediate_nearby": enriched})

        # 1) Batch-prefetch unique project postcodes (single HTTP call)
        unique_pcs = sorted({
            self._norm_pc(p.get('postcode', ''))
            for p in projects_list
            if p.get('postcode')
        })
        self._warm_coords_batch(unique_pcs)

        # 2) Compute distances locally (no per-row network)
        enriched = []
        for project in projects_list:
            d = self.get_postcode_distance(user_postcode, project.get('postcode', ''))
            proj = project.copy()
            proj['distance_miles'] = d
            enriched.append(proj)

        # 3) Filter and categorize
        in_radius = [
            p for p in enriched
            if p['distance_miles'] is not None and p['distance_miles'] <= prefs['max_radius_miles']
        ]

        immediate_nearby = [
            p for p in in_radius
            if p['distance_miles'] <= prefs['preferred_radius_miles']
        ]

        # 4) Sort by distance
        immediate_nearby.sort(key=lambda x: x['distance_miles'])

        return {"immediate_nearby": immediate_nearby}

    # Keep your existing category sorter so the controller doesn’t change
    def _sort_and_limit_recommendations(self, recommendations):
        recommendations['immediate_nearby'] = sorted(
            recommendations['immediate_nearby'],
            key=lambda x: (x.get('distance_miles') if x.get('distance_miles') is not None else 1e9)
        )
        return recommendations


class UserService:
    """
    Handles user-related business logic for recommendations
    (reads trader prefs and normalizes to miles).
    """

    @staticmethod
    def get_user_preferences(trader_profile):
        # Prefer numbers; tolerate strings/nulls
        raw = getattr(trader_profile, 'radiusKm', None)
        try:
            radius_km = float(raw) if raw not in (None, '', 'null', 'undefined') else 15.0
        except (TypeError, ValueError):
            radius_km = 15.0

        # Sanity clamp
        radius_km = max(1.0, min(radius_km, 200.0))
        radius_miles = round(radius_km * 0.621371, 1)

        return {
            'max_radius_miles': radius_miles,
            'preferred_radius_miles': radius_miles,
            'radius_km': radius_km,  # optional, handy for echoing to UI
        }

    @staticmethod
    def get_recommendation_explanations(user_postcode, preferences):
        return {
            'immediate_nearby': (
                f"Projects within {preferences['preferred_radius_miles']} miles of {user_postcode}"
            ),
        }
