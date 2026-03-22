"""Reusable inline keyboard factories."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def meal_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="meal_confirm"),
            InlineKeyboardButton("✏️ Edit", callback_data="meal_edit"),
            InlineKeyboardButton("❌ Cancel", callback_data="meal_cancel"),
        ]
    ])


def activity_keyboard() -> InlineKeyboardMarkup:
    levels = [
        ("1 — Sedentary", "act_1"),
        ("2 — Light", "act_2"),
        ("3 — Moderate", "act_3"),
        ("4 — Heavy", "act_4"),
        ("5 — Very Hard", "act_5"),
    ]
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=cb)] for label, cb in levels]
    )


def goal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔻 Cut", callback_data="goal_cut"),
            InlineKeyboardButton("⚖️ Maintain", callback_data="goal_maintain"),
            InlineKeyboardButton("🔺 Bulk", callback_data="goal_bulk"),
        ]
    ])


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👨 Male", callback_data="gender_male"),
            InlineKeyboardButton("👩 Female", callback_data="gender_female"),
        ]
    ])
