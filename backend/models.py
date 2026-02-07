"""
SQLAlchemy models for User and Run.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    azure_ad_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    runs: Mapped[List["Run"]] = relationship(back_populates="user")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    deal_id: Mapped[str] = mapped_column(String(50), nullable=False)
    deal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    answers_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sources_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stats_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    excel_blob_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    baseline_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    transcript_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="runs")

    __table_args__ = (
        Index("idx_runs_deal", "deal_id"),
        Index("idx_runs_user", "user_id"),
    )
