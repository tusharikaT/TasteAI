import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMService:
    def __init__(self, api_key=None, model=None):
        """
        Initialize the LLM Integration Service.
        
        Parameters:
        - api_key (str, optional): Groq API key. If not provided, reads from GROQ_API_KEY env var.
        - model (str, optional): Groq model name. If not provided, reads from GROQ_MODEL env var,
          falling back to 'llama-3.3-70b-versatile'.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Please configure it in your .env file or pass it to the constructor."
            )
            
        self.client = Groq(api_key=self.api_key)
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def recommend_restaurants(self, candidates, preferences):
        """
        Call Groq API using JSON mode to rank and justify restaurant recommendations.
        
        Parameters:
        - candidates (list of dict): Candidate restaurants pre-filtered by the DB engine.
        - preferences (dict): User preferences containing:
          - location (str)
          - max_budget (int, optional)
          - cuisines (list of str, optional)
          - min_rating (float, optional)
          - additional_notes (str, optional)
          
        Returns:
        - dict: Structured JSON recommendation containing ranked lists and AI justifications.
        """
        if not candidates:
            return {
                "recommendations": [],
                "summaryOfChoice": "No candidate restaurants were provided for analysis."
            }

        # Setup System Instructions
        system_instruction = (
            "You are an expert culinary guide and personalized restaurant recommendation assistant.\n"
            "You are provided with a list of candidate restaurants (JSON format) and a user's preferences.\n"
            "Your task is to evaluate the candidates, select the top 5 that best match the user's preferences, "
            "rank them, and provide tailored explanations of why they are suitable.\n\n"
            "Strict Evaluation Guidelines:\n"
            "1. Recommend ONLY restaurants present in the provided candidates list. Never invent or hallucinate new ones.\n"
            "2. Rank the recommendations in descending order of suitability (rank 1 is the best match).\n"
            "3. Assess suitability based on city/location, budget (average_cost), cuisines, and rating, "
            "as well as any specific vibe or preferences requested in the user's additional notes.\n"
            "4. For each recommendation, provide a detailed and natural 'aiExplanation' justifying the fit.\n"
            "5. If available in the candidate's description, reviews, or dishes, suggest a few recommended dishes.\n\n"
            "You must output your response in a single, valid JSON object matching the following schema:\n"
            "{\n"
            "  \"recommendations\": [\n"
            "    {\n"
            "      \"restaurantId\": \"the ID of the restaurant (as a string or integer, matching the candidate's 'id')\",\n"
            "      \"name\": \"the name of the restaurant\",\n"
            "      \"rank\": 1,\n"
            "      \"suitabilityScore\": 95, // percentage match score (integer, e.g. 0-100)\n"
            "      \"aiExplanation\": \"justification text detailing why this restaurant fits their preferences (budget, cuisines, vibe)\",\n"
            "      \"recommendedDishesSuggest\": [\"suggested dish 1\", \"suggested dish 2\"] // optional\n"
            "    }\n"
            "  ],\n"
            "  \"summaryOfChoice\": \"A brief summary summarizing the overall recommendation selection.\"\n"
            "}\n\n"
            "Enforce strict JSON output. Do not include markdown code block backticks (e.g. ```json ... ```) in your raw response."
        )

        # Format User preferences and candidate information for the prompt
        from filtering_engine import BUDGET_TIER_LABELS
        location = preferences.get("location", "Not Specified")
        budget_tier = preferences.get("budget_tier")
        budget_display = BUDGET_TIER_LABELS.get(
            (budget_tier or "").strip().lower(), "Any Budget"
        )
        cuisines = ", ".join(preferences.get("cuisines", [])) if preferences.get("cuisines") else "Any Cuisine"
        min_rating = preferences.get("min_rating", "Any Rating")
        additional_notes = preferences.get("additional_notes", "None")

        user_prompt = (
            f"=== USER PREFERENCES ===\n"
            f"- Location/City: {location}\n"
            f"- Budget Tier: {budget_display}\n"
            f"- Cuisines: {cuisines}\n"
            f"- Minimum Rating: {min_rating}\n"
            f"- Additional Vibe/Vibe Notes: {additional_notes}\n\n"
            f"=== CANDIDATE RESTAURANTS (DB pre-filtered) ===\n"
            f"{json.dumps(candidates, indent=2)}\n\n"
            f"=== TASK ===\n"
            f"Evaluate the candidates, select the top 5 matches, rank them, and output your recommendation report in strict JSON format."
        )

        # Call the Groq chat completion endpoint with JSON mode enabled
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Low temperature for deterministic/reliable structures
            max_tokens=2048
        )

        raw_content = response.choices[0].message.content.strip()
        
        # Parse and return structured JSON
        try:
            parsed_recommendations = json.loads(raw_content)
            return parsed_recommendations
        except json.JSONDecodeError as e:
            # Fallback wrapper if parsing fails (extremely rare with JSON mode enabled)
            print(f"Error: Groq response did not contain valid JSON: {e}")
            print(f"Raw content: {raw_content}")
            raise e

if __name__ == "__main__":
    # Test stub
    try:
        service = LLMService()
        print(f"Groq API connection initialized with model: {service.model}")
    except Exception as e:
        print("Initialization failed (likely GROQ_API_KEY missing):", e)
