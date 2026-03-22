"""
BMR / TDEE / macro target calculations.

Formula used:
  BMR  — Mifflin-St Jeor
  TDEE — BMR × activity multiplier
  Targets adjusted for goal (cut / bulk / maintain)
"""
from __future__ import annotations

ACTIVITY_MULTIPLIERS = {
    1: 1.2,    # Sedentary
    2: 1.375,  # Light exercise 1-3 days/week
    3: 1.55,   # Moderate exercise 3-5 days/week
    4: 1.725,  # Heavy exercise 6-7 days/week
    5: 1.9,    # Very hard / physical job
}

GOAL_CALORIE_DELTA = {
    "cut": -500,
    "maintain": 0,
    "bulk": +300,
}

# Protein targets (g per kg body weight)
PROTEIN_PER_KG = {
    "cut": 2.2,
    "maintain": 1.8,
    "bulk": 2.0,
}


def calculate_targets(
    age: int,
    gender: str,
    weight_kg: float,
    height_cm: float,
    activity_level: int,
    goal: str,
) -> dict[str, int]:
    """Return daily calorie and macro targets."""
    # Mifflin-St Jeor BMR
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    tdee = bmr * multiplier
    daily_calories = round(tdee + GOAL_CALORIE_DELTA.get(goal, 0))

    protein_g = round(weight_kg * PROTEIN_PER_KG.get(goal, 1.8))
    fat_g = round(daily_calories * 0.25 / 9)          # 25 % of calories from fat
    carbs_kcal = daily_calories - protein_g * 4 - fat_g * 9
    carbs_g = round(max(carbs_kcal, 0) / 4)

    return {
        "daily_calories": daily_calories,
        "daily_protein_g": protein_g,
        "daily_carbs_g": carbs_g,
        "daily_fat_g": fat_g,
    }
