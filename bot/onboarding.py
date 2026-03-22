"""
Onboarding conversation handler.

States:
  AGE → GENDER → WEIGHT → HEIGHT → ACTIVITY → GOAL → DONE
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.keyboards import activity_keyboard, gender_keyboard, goal_keyboard
from database.crud import upsert_user
from services.nutrition import calculate_targets

logger = logging.getLogger(__name__)

# Conversation states
AGE, GENDER, WEIGHT, HEIGHT, ACTIVITY, GOAL = range(6)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Welcome to *Cykdro* — your AI nutrition tracker\\!\n\n"
        "Let's set up your profile\\. First, how old are you? \\(enter a number\\)",
        parse_mode="MarkdownV2",
    )
    return AGE


# ---------------------------------------------------------------------------
# Step handlers
# ---------------------------------------------------------------------------

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or not (10 <= int(text) <= 120):
        await update.message.reply_text("Please enter a valid age (10–120).")
        return AGE

    context.user_data["age"] = int(text)
    await update.message.reply_text(
        "What is your gender?", reply_markup=gender_keyboard()
    )
    return GENDER


async def ask_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["gender"] = query.data.split("_")[1]  # "male" or "female"
    await query.edit_message_text("What is your current weight in **kg**? (e.g. 75.5)", parse_mode="Markdown")
    return WEIGHT


async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight = float(update.message.text.strip().replace(",", "."))
        assert 20 <= weight <= 500
    except (ValueError, AssertionError):
        await update.message.reply_text("Please enter a valid weight in kg (e.g. 75.5).")
        return WEIGHT

    context.user_data["weight_kg"] = weight
    await update.message.reply_text("What is your height in **cm**? (e.g. 178)", parse_mode="Markdown")
    return HEIGHT


async def ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = float(update.message.text.strip().replace(",", "."))
        assert 50 <= height <= 300
    except (ValueError, AssertionError):
        await update.message.reply_text("Please enter a valid height in cm (e.g. 178).")
        return HEIGHT

    context.user_data["height_cm"] = height
    await update.message.reply_text(
        "What is your activity level?", reply_markup=activity_keyboard()
    )
    return ACTIVITY


async def ask_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["activity_level"] = int(query.data.split("_")[1])
    await query.edit_message_text("What is your goal?", reply_markup=goal_keyboard())
    return GOAL


async def ask_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["goal"] = query.data.split("_")[1]  # cut | maintain | bulk

    ud = context.user_data
    targets = calculate_targets(
        age=ud["age"],
        gender=ud["gender"],
        weight_kg=ud["weight_kg"],
        height_cm=ud["height_cm"],
        activity_level=ud["activity_level"],
        goal=ud["goal"],
    )

    user_row = {
        "id": update.effective_user.id,
        "username": update.effective_user.username,
        **{k: ud[k] for k in ("age", "gender", "weight_kg", "height_cm", "activity_level", "goal")},
        **targets,
    }
    upsert_user(user_row)

    goal_label = {"cut": "🔻 Cut", "maintain": "⚖️ Maintain", "bulk": "🔺 Bulk"}[ud["goal"]]
    await query.edit_message_text(
        f"✅ *Profile saved\\!*\n\n"
        f"🎯 Goal: {goal_label}\n"
        f"🔥 Daily Target: *{targets['daily_calories']} kcal*\n"
        f"🥩 Protein: *{targets['daily_protein_g']} g*\n"
        f"🍞 Carbs:   *{targets['daily_carbs_g']} g*\n"
        f"🧈 Fat:     *{targets['daily_fat_g']} g*\n\n"
        "Now send me a 📸 photo or a text description of your meal to start tracking\\!",
        parse_mode="MarkdownV2",
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Onboarding cancelled. Use /start to begin again.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------

def build_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            GENDER:   [CallbackQueryHandler(ask_gender, pattern="^gender_")],
            WEIGHT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_weight)],
            HEIGHT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_height)],
            ACTIVITY: [CallbackQueryHandler(ask_activity, pattern="^act_")],
            GOAL:     [CallbackQueryHandler(ask_goal, pattern="^goal_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        name="onboarding",
        persistent=False,
    )
