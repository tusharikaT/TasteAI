"""
Verification script: Checks Phases 1-4 of the implementation plan.
"""
import os
import sys
import json
import sqlite3
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
results = []


def record(phase, test_name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((phase, test_name, passed, detail))
    print(f"  {status} {test_name}" + (f" — {detail}" if detail else ""))


# ============================================================
# PHASE 1: Environment Setup & Data Ingestion Pipeline
# ============================================================
print("\n" + "=" * 60)
print("PHASE 1: Environment Setup & Data Ingestion Pipeline")
print("=" * 60)

# 1a. CSV downloaded
csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "zomato.csv"))
csv_exists = os.path.exists(csv_path)
csv_size = os.path.getsize(csv_path) if csv_exists else 0
record("P1", "CSV dataset exists", csv_exists, f"{csv_size / (1024*1024):.1f} MB" if csv_exists else "NOT FOUND")

# 1b. SQLite DB created
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "zomato.db"))
db_exists = os.path.exists(db_path)
record("P1", "SQLite database exists", db_exists)

# 1c. DB has records
if db_exists:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM restaurants")
    count = cur.fetchone()[0]
    record("P1", "Database has records", count > 0, f"{count} records")

    # 1d. Ingestion script module importable
    try:
        from ingestion import download_dataset, seed_database
        record("P1", "ingestion.py importable", True)
    except Exception as e:
        record("P1", "ingestion.py importable", False, str(e))
else:
    record("P1", "Database has records", False, "DB file missing")

# ============================================================
# PHASE 2: Core Database & Filtering Engine
# ============================================================
print("\n" + "=" * 60)
print("PHASE 2: Core Database & Filtering Engine")
print("=" * 60)

# 2a. Indexes exist
if db_exists:
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [r[0] for r in cur.fetchall()]
    has_city_idx = any("city" in idx for idx in indexes)
    has_cost_idx = any("cost" in idx for idx in indexes)
    has_rating_idx = any("rating" in idx for idx in indexes)
    record("P2", "Index on 'city'", has_city_idx, str(indexes))
    record("P2", "Index on 'average_cost'", has_cost_idx)
    record("P2", "Index on 'rating'", has_rating_idx)
    conn.close()

# 2b. RestaurantFilteringEngine importable
try:
    from filtering_engine import RestaurantFilteringEngine, BUDGET_TIERS, resolve_budget_tier
    record("P2", "RestaurantFilteringEngine importable", True)
except Exception as e:
    record("P2", "RestaurantFilteringEngine importable", False, str(e))

# 2b2. Budget tier constants exist
try:
    tiers_ok = all(k in BUDGET_TIERS for k in ["low", "medium", "high"])
    record("P2", "BUDGET_TIERS has low/medium/high", tiers_ok, str(BUDGET_TIERS))
    record("P2", "resolve_budget_tier('low') == 300", resolve_budget_tier("low") == 300)
    record("P2", "resolve_budget_tier('high') is None", resolve_budget_tier("high") is None)
except Exception as e:
    record("P2", "Budget tier constants", False, str(e))

# 2c. Validation milestone: get_candidates with budget_tier="low" returns <= 15, cost <= 300
try:
    engine = RestaurantFilteringEngine()
    candidates = engine.get_candidates("Banashankari", ["Cafe"], budget_tier="low")
    within_limit = len(candidates) <= 15
    record("P2", "get_candidates returns <= 15 results", within_limit, f"got {len(candidates)}")

    budget_ok = all(
        c.get("average_cost") is None or c["average_cost"] <= 300
        for c in candidates
    )
    record("P2", "All results within 'low' tier cap (<=300)", budget_ok)

    # 2d. Sorted by rating DESC, votes DESC
    sorted_ok = True
    for i in range(len(candidates) - 1):
        curr = candidates[i]
        nxt = candidates[i + 1]
        if curr["rating"] is not None and nxt["rating"] is not None:
            if curr["rating"] < nxt["rating"]:
                sorted_ok = False
                break
            if curr["rating"] == nxt["rating"]:
                if (curr["votes"] or 0) < (nxt["votes"] or 0):
                    sorted_ok = False
                    break
    record("P2", "Results sorted by rating DESC, votes DESC", sorted_ok)

    # 2e. Cuisine filter works
    for c in candidates:
        cuisines_lower = [x.lower() for x in c.get("cuisines", [])]
        if "cafe" not in cuisines_lower:
            record("P2", "Cuisine filter correctness", False, f"{c['name']} has {c['cuisines']}")
            break
    else:
        record("P2", "Cuisine filter correctness", True)

except Exception as e:
    record("P2", "Filtering engine validation", False, str(e))


# ============================================================
# PHASE 3: Groq LLM Integration Service
# ============================================================
print("\n" + "=" * 60)
print("PHASE 3: Groq LLM Integration Service")
print("=" * 60)

# 3a. LLMService importable
try:
    from llm_service import LLMService
    record("P3", "LLMService importable", True)
except Exception as e:
    record("P3", "LLMService importable", False, str(e))

# 3b. GROQ_API_KEY configured
api_key = os.getenv("GROQ_API_KEY", "")
key_configured = bool(api_key) and api_key != "your_groq_api_key_here"
record("P3", "GROQ_API_KEY configured", key_configured)

# 3c. Groq client initialises
if key_configured:
    try:
        service = LLMService()
        record("P3", "Groq client initialises", True, f"model={service.model}")
    except Exception as e:
        record("P3", "Groq client initialises", False, str(e))

    # 3d. JSON mode & structured output
    try:
        test_candidates = engine.get_candidates("Banashankari", ["Cafe"], budget_tier="medium", min_rating=3.5, limit=5)
        test_prefs = {
            "location": "Banashankari",
            "cuisines": ["Cafe"],
            "budget_tier": "medium",
            "min_rating": 3.5,
        }
        result = service.recommend_restaurants(test_candidates, test_prefs)
        has_recs = "recommendations" in result and isinstance(result["recommendations"], list)
        has_summary = "summaryOfChoice" in result
        record("P3", "Groq returns 'recommendations' key", has_recs, f"{len(result.get('recommendations', []))} items")
        record("P3", "Groq returns 'summaryOfChoice' key", has_summary)

        if has_recs and len(result["recommendations"]) > 0:
            rec = result["recommendations"][0]
            fields_ok = all(k in rec for k in ["restaurantId", "name", "rank", "suitabilityScore", "aiExplanation"])
            record("P3", "Recommendation has required fields", fields_ok)
            score_ok = isinstance(rec.get("suitabilityScore"), int) and 0 <= rec["suitabilityScore"] <= 100
            record("P3", "suitabilityScore is int 0-100", score_ok, f"score={rec.get('suitabilityScore')}")
    except Exception as e:
        record("P3", "Groq structured output validation", False, str(e))
else:
    record("P3", "Groq client initialises", False, "API key not configured — skipping live tests")


# ============================================================
# PHASE 4: Orchestrator & Application Layer
# ============================================================
print("\n" + "=" * 60)
print("PHASE 4: Orchestrator & Application Layer")
print("=" * 60)

# 4a. RecommendationOrchestrator importable
try:
    from orchestrator import RecommendationOrchestrator
    record("P4", "RecommendationOrchestrator importable", True)
except Exception as e:
    record("P4", "RecommendationOrchestrator importable", False, str(e))

# 4b. Pipeline: request -> filtering -> LLM -> payload
try:
    orch = RecommendationOrchestrator()
    prefs = {
        "location": "Banashankari",
        "cuisines": ["Cafe"],
        "budget_tier": "medium",
        "min_rating": 3.5,
        "additional_notes": "cozy coffee spot",
    }
    result = orch.get_recommendations(prefs)
    has_recs = "recommendations" in result and len(result["recommendations"]) > 0
    record("P4", "Orchestrator returns recommendations", has_recs, f"{len(result.get('recommendations', []))} items")
    record("P4", "Response has 'fallback' flag", "fallback" in result, f"fallback={result.get('fallback')}")
    record("P4", "Response has 'cached' flag", "cached" in result, f"cached={result.get('cached')}")
except Exception as e:
    record("P4", "Orchestrator pipeline", False, str(e))

# 4c. Caching (1-hour TTL)
try:
    result2 = orch.get_recommendations(prefs)
    cache_works = result2.get("cached") is True
    record("P4", "Identical query returns cached=True", cache_works)

    stats = orch.cache_stats()
    ttl_ok = stats.get("ttl_seconds") == 3600
    record("P4", "Cache TTL is 3600s (1 hour)", ttl_ok, f"ttl={stats.get('ttl_seconds')}")
except Exception as e:
    record("P4", "Caching validation", False, str(e))

# 4d. Graceful degradation / fallback
try:
    orch_fallback = RecommendationOrchestrator()
    # Sabotage the LLM service with an invalid key
    orch_fallback._llm_service = LLMService.__new__(LLMService)
    orch_fallback._llm_service.api_key = "invalid_key_for_testing"
    orch_fallback._llm_service.model = "llama-3.3-70b-versatile"

    from groq import Groq
    orch_fallback._llm_service.client = Groq(api_key="gsk_invalid_key_00000000000000000000000000000000000000000000000")

    fallback_result = orch_fallback.get_recommendations(prefs)
    is_fallback = fallback_result.get("fallback") is True
    record("P4", "Fallback activates on LLM failure", is_fallback, f"fallback={fallback_result.get('fallback')}")

    msg = fallback_result.get("summaryOfChoice", "")
    correct_msg = "AI reasoning is currently offline" in msg
    record("P4", "Fallback message is correct", correct_msg, f'"{msg[:60]}..."')

    has_fallback_recs = len(fallback_result.get("recommendations", [])) > 0
    record("P4", "Fallback still returns DB results", has_fallback_recs)
except Exception as e:
    record("P4", "Fallback/degradation validation", False, str(e))

# 4e. API layer (FastAPI)
try:
    from api import app
    routes = [r.path for r in app.routes]
    has_recommend = "/recommend" in routes
    has_health = "/health" in routes
    record("P4", "FastAPI app importable", True)
    record("P4", "POST /recommend endpoint exists", has_recommend, str(routes))
    record("P4", "GET /health endpoint exists", has_health)
except Exception as e:
    record("P4", "FastAPI app validation", False, str(e))

# 4f. test_api.py port mismatch
try:
    with open(os.path.join(os.path.dirname(__file__), "test_api.py"), "r") as f:
        test_content = f.read()
    port_in_env = os.getenv("PORT", "8000")
    if f"localhost:{port_in_env}" in test_content:
        record("P4", "test_api.py BASE_URL matches .env PORT", True, f"PORT={port_in_env}")
    else:
        # Check what port test_api uses
        import re
        m = re.search(r"localhost:(\d+)", test_content)
        test_port = m.group(1) if m else "unknown"
        record("P4", "test_api.py BASE_URL matches .env PORT", False,
               f"test uses :{test_port}, .env PORT={port_in_env}")
except Exception as e:
    record("P4", "test_api.py port check", False, str(e))


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

total = len(results)
passed = sum(1 for r in results if r[2])
failed = sum(1 for r in results if not r[2])
print(f"\n  Total checks: {total}")
print(f"  {PASS} Passed:  {passed}")
print(f"  {FAIL} Failed:  {failed}")

if failed > 0:
    print(f"\n  Failed checks:")
    for phase, name, ok, detail in results:
        if not ok:
            print(f"    {FAIL} [{phase}] {name}" + (f" — {detail}" if detail else ""))
print()
