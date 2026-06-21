import os
import sys
import time
import json
import hashlib
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# ---------------------------------------------------------------------------
# Lazy imports so the orchestrator can be imported without crashing if the
# caller is running unit tests that mock the sub-services.
# ---------------------------------------------------------------------------
from filtering_engine import RestaurantFilteringEngine
from llm_service import LLMService


# ---------------------------------------------------------------------------
# Cache Configuration
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 3600  # 1 hour


def _make_cache_key(preferences: dict) -> str:
    """
    Create a deterministic cache key from the user preferences dict.
    Only the fields that affect query results are included so that
    irrelevant fields (e.g. additional_notes phrasing) don't bust the cache.
    """
    key_data = {
        "location": (preferences.get("location") or "").strip().lower(),
        "cuisines": sorted(
            [c.strip().lower() for c in (preferences.get("cuisines") or []) if c.strip()]
        ),
        "budget_tier": (preferences.get("budget_tier") or "").strip().lower(),
        "min_rating": preferences.get("min_rating"),
    }
    serialised = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class RecommendationOrchestrator:
    """
    Orchestrates the full recommendation pipeline:
      1. Query the Filtering Engine for pre-filtered candidates.
      2. Pass candidates to the LLM Service for AI-ranked recommendations.
      3. Cache results for identical queries (TTL = 1 hour).
      4. Gracefully degrade to ratings-based results if LLM is unavailable.
    """

    def __init__(self):
        self.filtering_engine = RestaurantFilteringEngine()
        self._llm_service: LLMService | None = None  # Lazy-initialised
        self._cache: dict[str, dict] = {}             # key -> {payload, expires_at}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_llm_service(self) -> LLMService:
        """Lazily create the LLM service so missing API keys surface at
        request time, not at import / startup time."""
        if self._llm_service is None:
            self._llm_service = LLMService()
        return self._llm_service

    def _get_cached(self, cache_key: str) -> dict | None:
        """Return a cached result if it exists and has not expired."""
        entry = self._cache.get(cache_key)
        if entry and time.time() < entry["expires_at"]:
            return entry["payload"]
        # Evict stale entry
        self._cache.pop(cache_key, None)
        return None

    def _set_cache(self, cache_key: str, payload: dict) -> None:
        """Store a result in the in-memory cache with a TTL."""
        self._cache[cache_key] = {
            "payload": payload,
            "expires_at": time.time() + CACHE_TTL_SECONDS,
        }

    def _fallback_response(self, candidates: list[dict], reason: str) -> dict:
        """
        Build a graceful-degradation response from raw DB candidates when
        the LLM is unavailable.  Candidates are already sorted by rating DESC
        (as returned by the filtering engine), so we just wrap them.
        """
        fallback_recs = []
        for idx, restaurant in enumerate(candidates[:5], start=1):
            fallback_recs.append({
                "restaurantId": str(restaurant.get("id", idx)),
                "name": restaurant.get("name", "Unknown"),
                "rank": idx,
                "suitabilityScore": None,          # No AI score in fallback mode
                "aiExplanation": None,              # No AI explanation in fallback mode
                "recommendedDishesSuggest": [],
                # Expose key DB fields so the frontend can still display cards
                "rating": restaurant.get("rating"),
                "average_cost": restaurant.get("average_cost"),
                "cuisines": restaurant.get("cuisines", []),
                "address": restaurant.get("address"),
                "online_order": bool(restaurant.get("online_order")),
                "book_table": bool(restaurant.get("book_table")),
                "votes": restaurant.get("votes"),
            })

        return {
            "recommendations": fallback_recs,
            "summaryOfChoice": (
                "AI reasoning is currently offline, displaying best ratings."
            ),
            "fallback": True,
            "fallback_reason": reason,
            "cached": False,
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_recommendations(self, preferences: dict) -> dict:
        """
        Main entry point for the orchestration pipeline.

        Parameters
        ----------
        preferences : dict
            Must contain at minimum ``location`` (str).
            Optional keys: ``cuisines`` (list[str]), ``max_budget`` (int),
            ``min_rating`` (float), ``additional_notes`` (str).

        Returns
        -------
        dict  with keys:
            - recommendations  (list)
            - summaryOfChoice  (str)
            - fallback         (bool)
            - cached           (bool)
        """
        # ----------------------------------------------------------------
        # 0. Validate required fields
        # ----------------------------------------------------------------
        location = (preferences.get("location") or "").strip()
        if not location:
            raise ValueError("'location' is a required field and must not be empty.")

        # ----------------------------------------------------------------
        # 1. Check in-memory cache
        # ----------------------------------------------------------------
        cache_key = _make_cache_key(preferences)
        cached_result = self._get_cached(cache_key)
        if cached_result is not None:
            # Return the cached payload with cached=True flag set
            return {**cached_result, "cached": True}

        # ----------------------------------------------------------------
        # 2. Query the Filtering Engine for DB candidates
        # ----------------------------------------------------------------
        candidates = self.filtering_engine.get_candidates(
            city=location,
            cuisines=preferences.get("cuisines") or None,
            budget_tier=preferences.get("budget_tier"),
            min_rating=preferences.get("min_rating"),
            limit=15,
        )

        if not candidates:
            # No DB matches at all — return an empty response immediately
            empty_payload = {
                "recommendations": [],
                "summaryOfChoice": (
                    f"No restaurants found in '{location}' matching the given criteria."
                ),
                "fallback": False,
                "cached": False,
            }
            return empty_payload

        # ----------------------------------------------------------------
        # 3. Call LLM Service — with fallback on ANY exception
        # ----------------------------------------------------------------
        try:
            llm = self._get_llm_service()
            ai_result = llm.recommend_restaurants(candidates, preferences)

            # Enrich AI recommendations with full DB data so the frontend
            # has everything it needs to render a card without extra calls.
            id_to_candidate = {str(c["id"]): c for c in candidates}
            for rec in ai_result.get("recommendations", []):
                rid = str(rec.get("restaurantId", ""))
                db_row = id_to_candidate.get(rid, {})
                rec.setdefault("rating", db_row.get("rating"))
                rec.setdefault("average_cost", db_row.get("average_cost"))
                rec.setdefault("cuisines", db_row.get("cuisines", []))
                rec.setdefault("address", db_row.get("address"))
                rec.setdefault("online_order", bool(db_row.get("online_order")))
                rec.setdefault("book_table", bool(db_row.get("book_table")))
                rec.setdefault("votes", db_row.get("votes"))

            payload = {
                **ai_result,
                "fallback": False,
                "cached": False,
            }

        except Exception as exc:
            # Graceful degradation — LLM unavailable
            reason = str(exc)
            print(f"[Orchestrator] LLM unavailable, activating fallback. Reason: {reason}")
            return self._fallback_response(candidates, reason)

        # ----------------------------------------------------------------
        # 4. Store in cache (only successful AI responses are cached)
        # ----------------------------------------------------------------
        self._set_cache(cache_key, payload)

        return payload

    def clear_cache(self) -> int:
        """Flush the entire in-memory cache. Returns number of entries removed."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def cache_stats(self) -> dict:
        """Return current cache statistics."""
        now = time.time()
        active = sum(1 for e in self._cache.values() if now < e["expires_at"])
        return {
            "total_entries": len(self._cache),
            "active_entries": active,
            "ttl_seconds": CACHE_TTL_SECONDS,
        }

    def get_cities(self) -> list[str]:
        """Fetch all unique cities available in the dataset."""
        return self.filtering_engine.get_cities()


# ---------------------------------------------------------------------------
# Smoke test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== RecommendationOrchestrator Smoke Test ===\n")

    orchestrator = RecommendationOrchestrator()

    test_preferences = {
        "location": "Banashankari",
        "cuisines": ["Cafe"],
        "budget_tier": "medium",
        "min_rating": 3.5,
        "additional_notes": "Looking for a cozy place with good coffee.",
    }

    print(f"Request: {json.dumps(test_preferences, indent=2)}\n")

    try:
        result = orchestrator.get_recommendations(test_preferences)
        print("=== Result ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Second call — should be cached
        print("\n--- Making identical request (should be cached) ---")
        result2 = orchestrator.get_recommendations(test_preferences)
        print(f"cached flag: {result2.get('cached')}")
        print(f"Cache stats: {orchestrator.cache_stats()}")

    except Exception as e:
        print(f"Error during smoke test: {e}")
