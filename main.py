import pandas as pd
import numpy as np
from openai import OpenAI
import json

# --- Initialize your OpenAI client ---
client = OpenAI(api_key="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")

# --- Step 1: Similarity filter: 2 out of 3 odds must match ---
def get_similar_matches(home_odds, draw_odds, away_odds, df, k=300):
    """
    Returns historical matches where at least 2 out of 3 odds match exactly.
    """
    mask_home = df["home_odds"] == home_odds
    mask_draw = df["draw_odds"] == draw_odds
    mask_away = df["away_odds"] == away_odds

    # Count how many odds match per row
    matches_count = mask_home.astype(float) + mask_draw.astype(float) + mask_away.astype(float)

    # Select rows where at least 2 match
    similar_matches = df[matches_count >= 2]

    # Limit to top k
    return similar_matches.head(k)

# --- Step 2: Build payload for ChatGPT ---
def build_payload(neighbors, home_odds, draw_odds, away_odds):
    payload = {
        "current_match_odds": {
            "home": home_odds,
            "draw": draw_odds,
            "away": away_odds
        },
        "sample_size": int(len(neighbors)),
        "similar_historical_matches": neighbors[[
            "home_odds", "draw_odds", "away_odds",
            "home_goals", "away_goals", "home_score", "away_score"
        ]].to_dict(orient="records")
    }
    return payload

# --- Step 3: ChatGPT agent ---
def ask_chatgpt(payload):
    system_prompt = """
You are a football betting market selection agent.
You are given ONLY historical match results from similar matches, with:
- home_odds, draw_odds, away_odds
- predicted scores: home_goals and away_goals
- final scores: home_score and away_score

Your tasks:
- Analyze frequencies and patterns in the historical odds.
- Use both home goals and away goals together with the home score and away score to derive possible betting markets:
  * Match Result (Home / Draw / Away)
  * Home Team Over/Under 1.5 Goals
  * Away Team Over/Under 1.5 Goals
  * Over/Under 1.5 Goals
  * Over/Under 2.5 Goals
  * Both Teams To Score (Yes / No)
  * Double Chance (1X / X2 / 12)
- Evaluate all markets and select the SINGLE strongest market.
- Select the BEST outcome within that market.
- Return a confidence level between 0 and 1.
- Use ONLY the supplied data.
- If no market is strong with confidence level below 0.95, return "insufficient evidence".

Return ONLY JSON, do not include explanations.
"""

    user_prompt = f"""
Historical matches with home goals and away goals, and final scores and odds:

{payload}

Return a JSON object with this structure:

{{
  "best_market": "Match Result | Over/Under 2.5 | BTTS | Double Chance | insufficient evidence",
  "best_outcome": "string or null",
  "expected_total_goals": "low | medium | high",
  "confidence": number between 0 and 1,
  "reasoning_summary": "short, data-driven explanation with figures and values of old stats"
}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1
    )

    return response.choices[0].message.content

# --- Step 4: Full pipeline ---
def fallback_market_from_data(neighbors):
    """
    Create a fallback market suggestion based on historical goals and scores.
    """
    if neighbors.empty:
        return {
            "best_market": "Fallback",
            "best_outcome": None,
            "expected_total_goals": "low",
            "confidence": 0,
            "reasoning_summary": "No historical matches available for fallback."
        }

    # Calculate some basic statistics from historical matches
    avg_home_goals = neighbors["home_goals"].mean()
    avg_away_goals = neighbors["away_goals"].mean()
    avg_total_goals = (neighbors["home_score"] + neighbors["away_score"]).mean()
    btts_frequency = ((neighbors["home_score"] > 0) & (neighbors["away_score"] > 0)).mean()

    # Decide fallback market based on stats
    if avg_home_goals > avg_away_goals:
        best_market = "Home Team Over/Under Goals"
        best_outcome = "Home Over 0.5 Goals"
    elif avg_away_goals > 2:
        best_market = "Away Team Over/Under Goals"
        best_outcome = "Away Over 0.5 Goals"
    elif avg_total_goals >= 2:
        best_market = "Over/Under 1.5 Goals"
        best_outcome = "Over 1.5 Goals"
    elif btts_frequency > 0.7:
        best_market = "Both Teams To Score"
        best_outcome = "Yes"
    else:
        best_market = "Over/Under 1.5 Goals"
        best_outcome = "Under 1.5 Goals"

    # Confidence is proportional to sample size and strength of statistic
    confidence = min(0.5 + 0.5 * (len(neighbors)/50), 0.8)  #scaling

    # Build reasoning summary
    reasoning = (
        f"Fallback based on {len(neighbors)} historical matches. "
        f"Avg home goals: {avg_home_goals:.2f}, "
        f"avg away goals: {avg_away_goals:.2f}, "
        f"avg total goals: {avg_total_goals:.2f}, "
        f"BTTS frequency: {btts_frequency:.2f}."
    )

    return {
        "best_market": best_market,
        "best_outcome": best_outcome,
        "expected_total_goals": "high" if avg_total_goals > 2 else "medium" if avg_total_goals > 1 else "low",
        "confidence": round(confidence, 2),
        "reasoning_summary": reasoning
    }

def predict_match(home_odds, draw_odds, away_odds, df, k=50):
    neighbors = get_similar_matches(home_odds, draw_odds, away_odds, df, k=k)
    if neighbors.empty:
        return fallback_market_from_data(neighbors)  # fallback if no matches

    payload = build_payload(neighbors, home_odds, draw_odds, away_odds)
    result = ask_chatgpt(payload)

    # If ChatGPT returns insufficient evidence, use data-driven fallback
    import json
    try:
        parsed = json.loads(result)
        if parsed.get("best_market") == "insufficient evidence":
            return fallback_market_from_data(neighbors)
        return parsed
    except:
        return fallback_market_from_data(neighbors)


# --- Example usage ---
if __name__ == "__main__":
    # Load your historical matches dataset
    # Must have columns: ["home_odds", "draw_odds", "away_odds", "home_goals", "away_goals", "home_score", "away_score"]
    df = pd.read_json(
    "https://raw.githubusercontent.com/Abeikuwill/Sportybet_Predictions/main/SourceBook.json"
    )


    # Predict for a new match
    A = float(input("Type the Home_Odds with all the decimals: "))
    B = float(input("Type the Draw_Odds with all the decimals: "))
    C = float(input("Type the Away_Odds with all the decimals: "))
    result = predict_match(A, B, C, df, k=300)
    print(result)



