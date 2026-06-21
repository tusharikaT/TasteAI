import unittest
from filtering_engine import RestaurantFilteringEngine

class TestRestaurantFilteringEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RestaurantFilteringEngine()

    def test_city_filter(self):
        """Verify filtering by city/neighborhood and applying limits."""
        city = "Banashankari"
        limit = 10
        results = self.engine.get_candidates(city=city, limit=limit)
        
        self.assertGreater(len(results), 0, f"No restaurants found for city: {city}")
        self.assertLessEqual(len(results), limit)
        for r in results:
            self.assertEqual(r['city'].lower(), city.lower(), f"City mismatch for {r['name']}: expected {city}, got {r['city']}")

    def test_budget_filter(self):
        """Verify filtering by budget tier (average cost for two) in local currency."""
        city = "Banashankari"
        budget_tier = "low"  # Low tier = average_cost <= 300
        max_cost_for_tier = 300
        results = self.engine.get_candidates(city=city, budget_tier=budget_tier)
        
        self.assertGreater(len(results), 0, f"No restaurants found with budget tier '{budget_tier}' in {city}")
        for r in results:
            if r['average_cost'] is not None:
                self.assertLessEqual(
                    r['average_cost'], 
                    max_cost_for_tier, 
                    f"Restaurant {r['name']} exceeds {budget_tier} tier cap of {max_cost_for_tier}: cost is {r['average_cost']}"
                )

    def test_rating_filter(self):
        """Verify filtering by minimum rating threshold."""
        city = "Banashankari"
        min_rating = 4.0
        results = self.engine.get_candidates(city=city, min_rating=min_rating)
        
        self.assertGreater(len(results), 0, f"No restaurants found with rating >= {min_rating} in {city}")
        for r in results:
            if r['rating'] is not None:
                self.assertGreaterEqual(
                    r['rating'], 
                    min_rating, 
                    f"Restaurant {r['name']} has rating {r['rating']} below threshold of {min_rating}"
                )

    def test_cuisine_filter(self):
        """Verify filtering by cuisines list (matching at least one specified cuisine)."""
        city = "Banashankari"
        cuisines = ["Cafe", "Mexican"]
        results = self.engine.get_candidates(city=city, cuisines=cuisines)
        
        self.assertGreater(len(results), 0, f"No restaurants matching cuisines {cuisines} in {city}")
        for r in results:
            cand_cuisines_lower = [c.lower().strip() for c in r['cuisines']]
            has_match = any(tc.lower().strip() in cand_cuisines_lower for tc in cuisines)
            self.assertTrue(
                has_match, 
                f"Restaurant {r['name']} has cuisines {r['cuisines']} which do not overlap with search {cuisines}"
            )

    def test_ranking_order(self):
        """Verify that candidates are sorted by rating DESC, then votes DESC."""
        city = "Banashankari"
        results = self.engine.get_candidates(city=city, limit=15)
        
        self.assertGreater(len(results), 1, "Need at least 2 results to test ranking order")
        for i in range(len(results) - 1):
            curr = results[i]
            nxt = results[i + 1]
            
            # Check rating ordering
            if curr['rating'] is not None and nxt['rating'] is not None:
                self.assertGreaterEqual(
                    curr['rating'], 
                    nxt['rating'], 
                    f"Ranking error: Rating of {curr['name']} ({curr['rating']}) is less than {nxt['name']} ({nxt['rating']})"
                )
                
                # Check votes ordering if ratings are equal
                if curr['rating'] == nxt['rating']:
                    self.assertGreaterEqual(
                        curr['votes'], 
                        nxt['votes'], 
                        f"Ranking error (tiebreaker): Votes of {curr['name']} ({curr['votes']}) is less than {nxt['name']} ({nxt['votes']}) for rating {curr['rating']}"
                    )

if __name__ == "__main__":
    unittest.main()
