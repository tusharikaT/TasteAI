import os
import json
import sys
import unittest
from dotenv import load_dotenv
from filtering_engine import RestaurantFilteringEngine
from llm_service import LLMService

# Ensure stdout uses UTF-8 encoding on Windows to prevent console encoding crashes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

class TestGroqIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify GROQ_API_KEY is present
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            raise unittest.SkipTest(
                "Skipping integration test: GROQ_API_KEY not configured or is using default placeholder in .env"
            )
        
        cls.filtering_engine = RestaurantFilteringEngine()
        cls.llm_service = LLMService()

    def test_end_to_end_recommendation(self):
        """Test full pipeline: Filtering DB candidates -> Sending to Groq -> Output structured JSON."""
        preferences = {
            "location": "Banashankari",
            "budget_tier": "medium",
            "cuisines": ["Cafe", "Italian"],
            "min_rating": 3.8,
            "additional_notes": "Rooftop dining, nice cozy vibe with good desserts."
        }

        print("\n--- [Step 1] Querying Candidates from SQLite ---")
        candidates = self.filtering_engine.get_candidates(
            city=preferences["location"],
            cuisines=preferences["cuisines"],
            budget_tier=preferences["budget_tier"],
            min_rating=preferences["min_rating"],
            limit=15
        )

        print(f"Candidates found: {len(candidates)}")
        for idx, c in enumerate(candidates, 1):
            print(f"  {idx}. {c['name']} | Rating: {c['rating']} | Cost: {c['average_cost']} | Cuisines: {c['cuisines']}")
        
        self.assertGreater(len(candidates), 0, "No candidate restaurants returned by the filtering engine.")

        print("\n--- [Step 2] Querying Recommendations from Groq API ---")
        result = self.llm_service.recommend_restaurants(candidates, preferences)
        
        print("\n=== AI Recommendation Result ===")
        print(json.dumps(result, indent=2))
        
        # Verify JSON keys and structure matches AIRecommendationResponse
        self.assertIn("recommendations", result, "JSON output missing 'recommendations' key")
        self.assertIn("summaryOfChoice", result, "JSON output missing 'summaryOfChoice' key")
        
        recs = result["recommendations"]
        self.assertIsInstance(recs, list, "'recommendations' value should be a list")
        self.assertGreater(len(recs), 0, "Recommendations list should not be empty")
        
        # Verify schema fields inside each recommendation
        for r in recs:
            self.assertIn("restaurantId", r, "Recommendation missing 'restaurantId'")
            self.assertIn("name", r, "Recommendation missing 'name'")
            self.assertIn("rank", r, "Recommendation missing 'rank'")
            self.assertIn("suitabilityScore", r, "Recommendation missing 'suitabilityScore'")
            self.assertIn("aiExplanation", r, "Recommendation missing 'aiExplanation'")
            
            # Type validations
            self.assertIsInstance(r["rank"], int, "'rank' should be an integer")
            self.assertIsInstance(r["suitabilityScore"], int, "'suitabilityScore' should be an integer")
            self.assertGreaterEqual(r["suitabilityScore"], 0)
            self.assertLessEqual(r["suitabilityScore"], 100)
            self.assertIsInstance(r["aiExplanation"], str, "'aiExplanation' should be a string")
            self.assertGreater(len(r["aiExplanation"]), 0, "'aiExplanation' should not be empty")

if __name__ == "__main__":
    # If run directly, print helpful instructions
    print("Running integration pipeline test. Ensure GROQ_API_KEY is set in your .env file.")
    unittest.main()
