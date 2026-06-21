import os
import sqlite3
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# Budget Tier Definitions
# ---------------------------------------------------------------------------
# Maps tier labels to maximum average_cost (for two) in INR.
# None means no upper limit.
BUDGET_TIERS = {
    "low": 300,       # Street food, quick bites — ≤ ₹300
    "medium": 800,    # Casual dining, cafés   — ≤ ₹800
    "high": None,     # Fine dining, no limit
}

BUDGET_TIER_LABELS = {
    "low": "Low (up to ₹300 for two)",
    "medium": "Medium (up to ₹800 for two)",
    "high": "High (no limit)",
}


def resolve_budget_tier(tier: str | None) -> int | None:
    """
    Resolve a budget tier label to a numeric cost cap.

    Parameters
    ----------
    tier : str or None
        One of "low", "medium", "high" (case-insensitive), or None.

    Returns
    -------
    int or None
        The maximum average_cost threshold, or None for no limit / unknown tier.
    """
    if tier is None:
        return None
    return BUDGET_TIERS.get(tier.strip().lower())

class RestaurantFilteringEngine:
    def __init__(self, db_path=None):
        """
        Initialize the Restaurant Filtering Engine.
        
        Parameters:
        - db_path (str, optional): Custom path to the SQLite database. 
          If not provided, reads from DB_PATH env var, or falls back to 'data/zomato.db'.
        """
        if db_path is None:
            db_path = os.getenv("DB_PATH")
            if not db_path:
                # Fallback to default path relative to project root
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                db_path = os.path.join(base_dir, "data", "zomato.db")
        
        self.db_path = os.path.abspath(db_path)

    def get_candidates(self, city, cuisines=None, budget_tier=None, min_rating=None, limit=15):
        """
        Query the local SQLite database for matching candidate restaurants.
        
        Parameters:
        - city (str): Neighborhood/area name to search (corresponds to 'city' column).
        - cuisines (list of str, optional): List of cuisines to match.
          A restaurant matches if it serves at least one of these cuisines.
        - budget_tier (str, optional): Budget tier label — "low", "medium", or "high".
          Resolved internally to a numeric cost cap via BUDGET_TIERS.
        - min_rating (float, optional): Minimum rating threshold (e.g., 4.0).
        - limit (int): Maximum number of candidates to return (default 15).
        
        Returns:
        - list of dict: Clean dictionary representations of candidate restaurants, 
          sorted by rating DESC, then votes DESC.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Build query components
            query = "SELECT DISTINCT r.* FROM restaurants r"
            if cuisines:
                # Use json_each to unpack the JSON array of cuisines stored in the database
                query += ", json_each(r.cuisines) je"
            
            query += " WHERE 1=1"
            params = []

            # Filter by City/Neighborhood (case-insensitive)
            if city:
                query += " AND LOWER(r.city) = LOWER(?)"
                params.append(city.strip())

            # Filter by Budget Tier (resolve tier label to numeric cap)
            max_budget = resolve_budget_tier(budget_tier)
            if max_budget is not None:
                query += " AND r.average_cost <= ?"
                params.append(max_budget)

            # Filter by Minimum Rating
            if min_rating is not None:
                query += " AND r.rating >= ?"
                params.append(min_rating)

            # Filter by Cuisines (case-insensitive intersection match)
            if cuisines:
                # Convert list to lower case and strip whitespace
                target_cuisines = [c.lower().strip() for c in cuisines if c.strip()]
                if target_cuisines:
                    placeholders = ", ".join("?" for _ in target_cuisines)
                    query += f" AND LOWER(je.value) IN ({placeholders})"
                    params.extend(target_cuisines)

            # Group by name and address to deduplicate entries representing identical listings
            query += " GROUP BY r.name, r.address"

            # Order by Rating DESC, then Votes DESC (to rank popular/well-rated first)
            query += " ORDER BY r.rating DESC, r.votes DESC LIMIT ?"
            params.append(limit)

            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Parse query results into standard dictionaries
            candidates = []
            for row in rows:
                item = dict(row)
                # Parse cuisines column from JSON text back to Python list
                if item.get("cuisines"):
                    try:
                        item["cuisines"] = json.loads(item["cuisines"])
                    except Exception:
                        item["cuisines"] = []
                else:
                    item["cuisines"] = []
                candidates.append(item)

            return candidates

        finally:
            conn.close()

    def get_cities(self):
        """
        Query the local SQLite database for all distinct cities.
        
        Returns:
        - list of str: A sorted list of unique city names.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT DISTINCT city FROM restaurants WHERE city IS NOT NULL AND city != '' ORDER BY city ASC")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

if __name__ == "__main__":
    # Quick debug run
    engine = RestaurantFilteringEngine()
    print("Database path in use:", engine.db_path)
    print(f"Budget Tiers: {BUDGET_TIERS}")
    try:
        for tier in ["low", "medium", "high"]:
            label = BUDGET_TIER_LABELS.get(tier, tier)
            sample_results = engine.get_candidates("Banashankari", cuisines=["Cafe"], budget_tier=tier, min_rating=3.5)
            print(f"\n[{label}] Found {len(sample_results)} matches.")
            for idx, res in enumerate(sample_results, 1):
                print(f"  {idx}. {res['name']} | Rating: {res['rating']} | Cost: {res['average_cost']} | Cuisines: {res['cuisines']}")
    except Exception as e:
        print("Error during test query:", e)
