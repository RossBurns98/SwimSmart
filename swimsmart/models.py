from .db import Base
from sqlalchemy import Column,Integer, String, Text, Date, JSON, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime as dt
import enum
class TrainingSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key= True, autoincrement= True)
    date: Mapped[dt.date] = mapped_column(Date, nullable= False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sets: Mapped[list["Set"]] = relationship( back_populates="session", cascade= "all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="sessions")
class Set(Base):
    __tablename__ = "sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable= False, index=True)
    distance_m: Mapped[int] = mapped_column(Integer, nullable= False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    stroke: Mapped[str] = mapped_column(String(20), nullable=False)
    rpe: Mapped[list[int]] = mapped_column(JSON, nullable= False)
    rep_times_sec: Mapped[list[int]] = mapped_column(JSON, nullable=False)

    session: Mapped["TrainingSession"] = relationship(back_populates="sets")

class UserRole(str, enum.Enum):
    coach = "coach"
    swimmer = "swimmer"

class User(Base):
    __tablename__ = "users"
    username = Column(String, unique=True, index=True, nullable=True)
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.swimmer)

    sessions = relationship("TrainingSession", back_populates="user")