"""
Database access helpers — all DB I/O lives here.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import Meal, SessionLocal, User


# ---------------------------------------------------------------------------
# Session context manager
# ---------------------------------------------------------------------------

@contextmanager
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_user(user_id: int) -> Optional[User]:
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is not None:
            db.expunge(user)
        return user


def upsert_user(data: dict) -> User:
    """Create or fully replace a user record."""
    with get_db() as db:
        user = db.query(User).filter(User.id == data["id"]).first()
        if user is None:
            user = User(**data)
            db.add(user)
        else:
            for key, value in data.items():
                setattr(user, key, value)
        db.flush()
        db.refresh(user)
        return user


# ---------------------------------------------------------------------------
# Meal helpers
# ---------------------------------------------------------------------------

def add_meal(
    user_id: int,
    description: str,
    calories: int,
    protein_g: int,
    carbs_g: int,
    fat_g: int,
    image_file_id: Optional[str] = None,
) -> Meal:
    with get_db() as db:
        meal = Meal(
            user_id=user_id,
            description=description,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            image_file_id=image_file_id,
            meal_date=date.today(),
        )
        db.add(meal)
        db.flush()
        db.refresh(meal)
        return meal


def delete_today_meals(user_id: int) -> int:
    """Delete all meals logged today. Returns the number of records deleted."""
    today = date.today()
    with get_db() as db:
        deleted = (
            db.query(Meal)
            .filter(Meal.user_id == user_id, Meal.meal_date == today)
            .delete(synchronize_session=False)
        )
        return deleted


def delete_user(user_id: int) -> bool:
    """Delete the user and all their meals (cascade). Returns True if user existed."""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            return False
        db.delete(user)
        return True


def is_user_active(user_id: int) -> bool:
    """Returns False if the user exists and is banned."""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            return True
        return bool(user.is_active)


def set_user_active(user_id: int, active: bool) -> Optional[User]:
    """Ban or unban a user. Returns the updated User or None if not found."""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            return None
        user.is_active = active
        db.flush()
        db.refresh(user)
        db.expunge(user)
        return user


def get_user_by_username(username: str) -> Optional[User]:
    """Find a user by Telegram username (with or without leading @)."""
    username = username.lstrip("@")
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if user is not None:
            db.expunge(user)
        return user


def get_all_user_ids() -> list[int]:
    """Return IDs of all active (non-banned) users."""
    with get_db() as db:
        rows = db.query(User.id).filter(User.is_active.is_(True)).all()
        return [r[0] for r in rows]


def get_all_users() -> list[User]:
    """Return all users ordered by join date (newest first)."""
    with get_db() as db:
        users = db.query(User).order_by(User.created_at.desc()).all()
        for u in users:
            db.expunge(u)
        return users


def get_stats() -> dict:
    """Return system-wide stats for the admin dashboard."""
    today = date.today()
    with get_db() as db:
        total_users = db.query(User).count()
        users_today = (
            db.query(User)
            .filter(func.date(User.created_at) == today)
            .count()
        )
        meals_today = db.query(Meal).filter(Meal.meal_date == today).count()
        banned_users = db.query(User).filter(User.is_active.is_(False)).count()
        return {
            "total_users": total_users,
            "users_today": users_today,
            "meals_today": meals_today,
            "banned_users": banned_users,
        }


def get_today_totals(user_id: int) -> dict:
    """Return summed macros for today."""
    today = date.today()
    with get_db() as db:
        meals = (
            db.query(Meal)
            .filter(Meal.user_id == user_id, Meal.meal_date == today)
            .all()
        )
        return {
            "calories": sum(m.calories for m in meals),
            "protein_g": sum(m.protein_g for m in meals),
            "carbs_g": sum(m.carbs_g for m in meals),
            "fat_g": sum(m.fat_g for m in meals),
            "meal_count": len(meals),
        }
