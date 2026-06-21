import urllib.request
import json

BASE_URL = "http://localhost:3000"

def test_health():
    req = urllib.request.urlopen(f"{BASE_URL}/health")
    health = json.loads(req.read())
    print("=== /health ===")
    print(json.dumps(health, indent=2))
    assert health["status"] == "ok"
    print("PASS: health check\n")

def test_recommend():
    payload = json.dumps({
        "location": "Banashankari",
        "cuisines": ["Cafe"],
        "budget_tier": "medium",
        "min_rating": 3.5,
        "additional_notes": "Cozy spot for coffee"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/recommend",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    print("=== /recommend (first call) ===")
    print("fallback:", resp["fallback"])
    print("cached:", resp["cached"])
    print("num recommendations:", len(resp["recommendations"]))
    for r in resp["recommendations"]:
        name = r["name"]
        rank = r["rank"]
        score = r["suitabilityScore"]
        rating = r["rating"]
        print(f"  {rank}. {name} | suitability={score}% | rating={rating}")
    print("summary:", resp["summaryOfChoice"][:80], "...")
    assert resp["fallback"] == False
    assert resp["cached"] == False
    assert len(resp["recommendations"]) > 0
    print("PASS: recommend\n")

def test_recommend_cached():
    payload = json.dumps({
        "location": "Banashankari",
        "cuisines": ["Cafe"],
        "budget_tier": "medium",
        "min_rating": 3.5,
        "additional_notes": "Cozy spot for coffee"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/recommend",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    print("=== /recommend (second call - should be cached) ===")
    print("cached:", resp["cached"])
    assert resp["cached"] == True
    print("PASS: caching works\n")

if __name__ == "__main__":
    test_health()
    test_recommend()
    test_recommend_cached()
    print("=== ALL TESTS PASSED ===")
