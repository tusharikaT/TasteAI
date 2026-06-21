# Backend API Documentation

This document describes the API endpoints provided by the FastAPI backend server of the TasteAI Restaurant Recommendation System. 

The server runs by default on `http://localhost:3000` (or `http://localhost:8000` depending on the environment configuration). It also automatically hosts an interactive Swagger documentation page at `/docs` or `/redoc`.

---

## 🛠️ Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/health` | Health Check |
| **POST** | `/recommend` | Get Restaurant Recommendations |
| **DELETE** | `/cache` | Clear Recommendation Cache |
| **GET** | `/cities` | Get Available Cities |
| **GET** | `/` | Serves the Frontend Static Webpage |

---

## 📋 Endpoint Details

### 1. Health Check
* **Endpoint:** `GET /health`
* **Description:** Returns the API status, configured database path, active Groq LLM model name, and cache statistics.

#### Response Example (200 OK)
```json
{
  "status": "ok",
  "service": "Restaurant Recommendation API",
  "version": "1.0.0",
  "groq_model": "llama-3.3-70b-versatile",
  "db_path": "data/zomato.db",
  "cache": {
    "hits": 12,
    "misses": 5,
    "size": 5
  }
}
```

---

### 2. Get Restaurant Recommendations
* **Endpoint:** `POST /recommend`
* **Description:** Submits the user's culinary preferences. The orchestrator queries the local SQLite database for candidate restaurants matching basic criteria, then applies AI reasoning using the Groq LLM to return ranked, tailored recommendations with justifications.
* **Caching:** Identical queries are cached in-memory for 1 hour. Subsequent duplicate requests return the cached result with `"cached": true`.
* **Fallback Mode:** If the Groq API fails or is rate-limited, the system falls back to database-filtered matches sorted strictly by ratings, setting `"fallback": true` and supplying the fallback reason.

#### Request Body Schema
```json
{
  "location": "Banashankari",
  "cuisines": ["Cafe", "Italian"],
  "budget_tier": "medium",
  "min_rating": 3.5,
  "additional_notes": "Looking for a cozy place with good desserts and outdoor seating."
}
```

* **Fields:**
  * `location` (string, Required): The neighborhood or city area to search.
  * `cuisines` (array of strings, Optional): Preferred cuisines. Leave empty to allow any cuisine.
  * `budget_tier` (string, Optional): Choice of `"low"` (≤ ₹300), `"medium"` (≤ ₹800), or `"high"` (no limit).
  * `min_rating` (float, Optional, default: `0.0`): Minimum acceptable rating (0.0 to 5.0).
  * `additional_notes` (string, Optional): Custom natural language preferences, vibe descriptions, or dietary requirements.

#### Response Body Schema (200 OK)
```json
{
  "recommendations": [
    {
      "restaurantId": 1205,
      "name": "Spice Garden Cafe",
      "rank": 1,
      "suitabilityScore": 95,
      "aiExplanation": "Perfect match as it is highly rated in Banashankari, serves exquisite Italian and Cafe items, and has a cozy outdoor courtyard ideal for dessert lovers.",
      "recommendedDishesSuggest": ["Tiramisu", "Pesto Pasta"],
      "rating": 4.3,
      "average_cost": 600,
      "budget_tier": "medium",
      "cuisines": ["Cafe", "Italian"],
      "address": "45, 100 Feet Road, Banashankari, Bangalore",
      "online_order": true,
      "book_table": false,
      "votes": 340
    }
  ],
  "summaryOfChoice": "Found several highly rated cafes and Italian spots in Banashankari. Recommended 'Spice Garden Cafe' as your top choice based on the cozy vibe and dessert preferences.",
  "fallback": false,
  "fallback_reason": null,
  "cached": false
}
```

---

### 3. Clear Recommendation Cache
* **Endpoint:** `DELETE /cache`
* **Description:** Clears all entries in the server-side recommendation cache. Useful during development or following data updates.

#### Response Example (200 OK)
```json
{
  "flushed_entries": 5,
  "status": "cache cleared"
}
```

---

### 4. Get Available Cities
* **Endpoint:** `GET /cities`
* **Description:** Retrieves all unique city names/regions present in the Zomato database. The frontend can use this list to populate search autocomplete or dropdown selections.

#### Response Example (200 OK)
```json
{
  "cities": [
    "Banashankari",
    "Basavanagudi",
    "Bellandur",
    "Brigade Road",
    "Brookefield",
    "Koramangala"
  ]
}
```

---

## 🛡️ Error Responses

* **422 Unprocessable Entity:** Returned if request parameters fail validation (e.g. missing required `location` field).
* **503 Service Unavailable:** 
  * If the database file is not initialized/accessible (Run `python src/ingestion.py` first).
  * If the Recommendation Orchestrator is still starting up.
* **500 Internal Server Error:** Returned in case of unexpected errors on the server.
