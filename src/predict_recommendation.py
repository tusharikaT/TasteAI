import json
import sys
from dotenv import load_dotenv
from filtering_engine import RestaurantFilteringEngine
from llm_service import LLMService

# Prevent Windows console encoding issues when outputting UTF-8 characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

import argparse

load_dotenv()

def predict():
    parser = argparse.ArgumentParser(description="Get restaurant recommendations using Filtering Engine & LLM")
    parser.add_argument("--location", type=str, required=True, help="Neighborhood/City name")
    parser.add_argument("--rating", type=float, default=0.0, help="Minimum rating")
    parser.add_argument("--budget", type=int, default=None, help="Maximum budget (average cost for two)")
    
    args = parser.parse_args()
    
    location = args.location
    min_rating = args.rating
    max_budget = args.budget

    print(f"=== Running Prediction for ===")
    print(f"Location: {location}")
    print(f"Min Rating: {min_rating}")
    print(f"Max Budget: {max_budget} INR\n")

    # Step 1: Filter candidates in the database
    engine = RestaurantFilteringEngine()
    preferences = {
        "location": location,
        "min_rating": min_rating,
        "max_budget": max_budget,
        "cuisines": None,
        "additional_notes": "Recommend the top 5 best-suited restaurants."
    }

    candidates = engine.get_candidates(
        city=preferences["location"],
        min_rating=preferences["min_rating"],
        max_budget=preferences["max_budget"],
        limit=15
    )

    print(f"[Step 1] Retrieved {len(candidates)} pre-filtered candidates from database:")
    for idx, c in enumerate(candidates, 1):
        print(f"  {idx}. {c['name']} | Rating: {c['rating']} | Cost: {c['average_cost']} | Cuisines: {c['cuisines']}")

    if not candidates:
        print("No candidates found matching the criteria in the database.")
        return

    # Step 2: Feed candidates to Groq LLM to predict top 5
    print("\n[Step 2] Sending candidates to Groq LLM for recommendation mapping...")
    llm = LLMService()
    recommendations = llm.recommend_restaurants(candidates, preferences)

    print("\n=== TOP 5 LLM RECOMMENDATIONS ===")
    print(json.dumps(recommendations, indent=2))

if __name__ == "__main__":
    predict()
