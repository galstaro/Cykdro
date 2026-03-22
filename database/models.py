from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date,
    ForeignKey, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)          # Telegram user ID
    username = Column(String, nullable=True)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)          # "male" | "female"
    weight_kg = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    activity_level = Column(Integer, nullable=False) # 1-5
    goal = Column(String, nullable=False)            # "cut" | "bulk" | "maintain"

    # Calculated targets (stored at onboarding, recalculated on profile update)
    daily_calories = Column(Integer, nullable=False)
    daily_protein_g = Column(Integer, nullable=False)
    daily_carbs_g = Column(Integer, nullable=False)
    daily_fat_g = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    meals = relationship("Meal", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} goal={self.goal} kcal={self.daily_calories}>"


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow)
    meal_date = Column(Date, default=date.today)

    description = Column(String, nullable=False)
    calories = Column(Integer, nullable=False)
    protein_g = Column(Integer, nullable=False)
    carbs_g = Column(Integer, nullable=False)
    fat_g = Column(Integer, nullable=False)

    # Telegram file_id of the original photo (null for text entries)
    image_file_id = Column(String, nullable=True)

    user = relationship("User", back_populates="meals")

    def __repr__(self) -> str:
        return (
            f"<Meal id={self.id} user={self.user_id} "
            f"kcal={self.calories} @ {self.meal_date}>"
        )


# ---------------------------------------------------------------------------
# Engine / session factory (imported by other modules)
# ---------------------------------------------------------------------------
engine = create_engine("sqlite:///cykdro.db", echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)
