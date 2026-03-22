"""Shared formatting helpers."""
from __future__ import annotations


def macro_bar(consumed: int, target: int, label: str, unit: str = "g") -> str:
    """Return a text progress bar line."""
    pct = min(consumed / target, 1.0) if target else 0
    filled = round(pct * 10)
    bar = "█" * filled + "░" * (10 - filled)
    remaining = max(target - consumed, 0)
    return f"{label}: {bar} {consumed}/{target}{unit} ({remaining}{unit} left)"


def format_analysis(data: dict) -> str:
    return (
        f"*{data['description']}*\n\n"
        f"🔥 Calories: *{data['calories']} kcal*\n"
        f"🥩 Protein:  *{data['protein']} g*\n"
        f"🍞 Carbs:    *{data['carbs']} g*\n"
        f"🧈 Fat:      *{data['fat']} g*"
    )


def format_status(totals: dict, user) -> str:
    lines = [
        "📊 *Today's Progress*\n",
        macro_bar(totals["calories"], user.daily_calories, "🔥 Calories", "kcal"),
        macro_bar(totals["protein_g"], user.daily_protein_g, "🥩 Protein"),
        macro_bar(totals["carbs_g"], user.daily_carbs_g, "🍞 Carbs"),
        macro_bar(totals["fat_g"], user.daily_fat_g, "🧈 Fat"),
        f"\n_Meals logged today: {totals['meal_count']}_",
    ]
    return "\n".join(lines)
