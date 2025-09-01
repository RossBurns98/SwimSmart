from .db import Base
from sqlalchemy import Integer, String, Text, Date, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime as dt

class TrainingSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key= True, autoincrement= True)
    date: Mapped[dt.date] = mapped_column(Date, nullable= False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sets: Mapped[list["Set"]] = relationship( back_populates="session", cascade= "all, delete-orphan")

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