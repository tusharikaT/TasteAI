import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# ---------------------------------------------------------------------------
# Import Orchestrator (lazy so startup doesn't crash without a DB)
# ---------------------------------------------------------------------------
from orchestrator import RecommendationOrchestrator

# ---------------------------------------------------------------------------
# Application lifespan — create a single shared orchestrator instance
# ---------------------------------------------------------------------------
orchestrator: RecommendationOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    print("[API] Starting up — initialising RecommendationOrchestrator...")
    orchestrator = RecommendationOrchestrator()
    print("[API] Orchestrator ready.")
    yield
    print("[API] Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI-Powered Restaurant Recommendation API",
    description=(
        "Backend API that combines local SQLite filtering with Groq LLM reasoning "
        "to return ranked, personalised restaurant recommendations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins so the Phase 5 frontend (any port/host) can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class RecommendationRequest(BaseModel):
    """User preferences sent by the frontend."""

    location: str = Field(
        ...,
        min_length=1,
        description="Neighbourhood or city area to search (e.g. 'Banashankari', 'Koramangala').",
        examples=["Banashankari"],
    )
    cuisines: list[str] = Field(
        default=[],
        description="List of preferred cuisines (e.g. ['Cafe', 'Italian']). Leave empty for any cuisine.",
        examples=[["Cafe", "Italian"]],
    )
    budget_tier: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Budget tier: 'low' (≤ ₹300), 'medium' (≤ ₹800), or 'high' (no limit).",
        examples=["medium"],
    )
    min_rating: float = Field(
        default=0.0,
        ge=0.0,
        le=5.0,
        description="Minimum acceptable rating threshold (0.0 – 5.0).",
        examples=[3.5],
    )
    additional_notes: str = Field(
        default="",
        description="Free-text vibe or preference notes (e.g. 'rooftop, family-friendly').",
        examples=["Looking for a cozy café with good desserts."],
    )


class RecommendationItem(BaseModel):
    """A single restaurant recommendation returned by the AI (or fallback)."""

    restaurantId: str | int
    name: str
    rank: int
    suitabilityScore: int | None = None
    aiExplanation: str | None = None
    recommendedDishesSuggest: list[str] = []
    # DB-enriched fields
    rating: float | None = None
    average_cost: int | None = None
    budget_tier: str | None = None
    cuisines: list[str] = []
    address: str | None = None
    online_order: bool = False
    book_table: bool = False
    votes: int | None = None


class RecommendationResponse(BaseModel):
    """Full response returned by the /recommend endpoint."""

    recommendations: list[RecommendationItem]
    summaryOfChoice: str
    fallback: bool = False
    fallback_reason: str | None = None
    cached: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    summary="Health Check",
    tags=["System"],
    response_description="Returns API status and current configuration.",
)
def health_check():
    """
    Lightweight health-check endpoint.
    Returns HTTP 200 with current status, model name, and database path.
    """
    import os as _os
    db_path = _os.getenv("DB_PATH", "data/zomato.db")
    groq_model = _os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    cache_stats = orchestrator.cache_stats() if orchestrator else {}

    return {
        "status": "ok",
        "service": "Restaurant Recommendation API",
        "version": "1.0.0",
        "groq_model": groq_model,
        "db_path": db_path,
        "cache": cache_stats,
    }


@app.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Get Restaurant Recommendations",
    tags=["Recommendations"],
    response_description="Ranked list of restaurant recommendations with AI explanations.",
)
def recommend(request: RecommendationRequest):
    """
    **Main recommendation endpoint.**

    Accepts user preferences and returns:
    - AI-ranked restaurant recommendations with natural-language explanations
      *(when Groq is available)*
    - Ratings-based fallback results *(when Groq is unavailable)*

    Identical requests are **cached for 1 hour** — repeated calls will include
    `"cached": true` in the response.
    """
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator is not initialised. The server may still be starting up.",
        )

    preferences = {
        "location": request.location,
        "cuisines": request.cuisines,
        "budget_tier": request.budget_tier,
        "min_rating": request.min_rating,
        "additional_notes": request.additional_notes,
    }

    try:
        result = orchestrator.get_recommendations(preferences)
    except ValueError as ve:
        # Bad request — invalid preferences (e.g. empty location)
        raise HTTPException(status_code=422, detail=str(ve))
    except FileNotFoundError as fe:
        # Database not found — likely ingest hasn't been run yet
        raise HTTPException(
            status_code=503,
            detail=f"Database not available: {fe}. Run 'python src/ingestion.py' first.",
        )
    except Exception as exc:
        # Unexpected server error
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")

    # Validate/coerce recommendation items via Pydantic
    recs = []
    for item in result.get("recommendations", []):
        recs.append(
            RecommendationItem(
                restaurantId=item.get("restaurantId", ""),
                name=item.get("name", ""),
                rank=item.get("rank", 0),
                suitabilityScore=item.get("suitabilityScore"),
                aiExplanation=item.get("aiExplanation"),
                recommendedDishesSuggest=item.get("recommendedDishesSuggest", []),
                rating=item.get("rating"),
                average_cost=item.get("average_cost"),
                cuisines=item.get("cuisines", []),
                address=item.get("address"),
                online_order=bool(item.get("online_order", False)),
                book_table=bool(item.get("book_table", False)),
                votes=item.get("votes"),
            )
        )

    return RecommendationResponse(
        recommendations=recs,
        summaryOfChoice=result.get("summaryOfChoice", ""),
        fallback=result.get("fallback", False),
        fallback_reason=result.get("fallback_reason"),
        cached=result.get("cached", False),
    )


@app.delete(
    "/cache",
    summary="Clear Recommendation Cache",
    tags=["System"],
    response_description="Returns the number of cache entries flushed.",
)
def clear_cache():
    """
    Flush all cached recommendation results.
    Useful for development or when the dataset has been re-ingested.
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised.")
    count = orchestrator.clear_cache()
    return {"flushed_entries": count, "status": "cache cleared"}


@app.get(
    "/cities",
    summary="Get Available Cities",
    tags=["System"],
    response_description="Returns a list of unique cities available in the dataset.",
)
def get_cities():
    """Fetch all unique cities available for filtering."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised.")
    try:
        cities = orchestrator.get_cities()
        return {"cities": cities}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")

# Mount static files at the root
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


# ---------------------------------------------------------------------------
# Entry-point for direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    print(f"[API] Starting server on http://0.0.0.0:{port}")
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
