import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    notion_integrations: Mapped[list["NotionIntegration"]] = relationship(back_populates="user")
    sis_integrations: Mapped[list["SISIntegration"]] = relationship(back_populates="user")
    workspace_configs: Mapped[list["WorkspaceConfig"]] = relationship(back_populates="user")
    sync_runs: Mapped[list["SyncRun"]] = relationship(back_populates="user")


class NotionIntegration(Base):
    __tablename__ = "notion_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    workspace_name: Mapped[Optional[str]] = mapped_column(Text)
    workspace_icon: Mapped[Optional[str]] = mapped_column(Text)
    bot_id: Mapped[Optional[str]] = mapped_column(Text)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="notion_integrations")
    workspace_config: Mapped[Optional["WorkspaceConfig"]] = relationship(back_populates="notion_integration")


class SISIntegration(Base):
    __tablename__ = "sis_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    service: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    base_url: Mapped[Optional[str]] = mapped_column(Text)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_validation_error: Mapped[Optional[str]] = mapped_column(Text)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sis_integrations")
    sync_runs: Mapped[list["SyncRun"]] = relationship(back_populates="sis_integration")


class WorkspaceConfig(Base):
    __tablename__ = "workspace_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    notion_integration_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notion_integrations.id"), unique=True, nullable=False, index=True)
    root_page_id: Mapped[Optional[str]] = mapped_column(Text)
    template_version: Mapped[Optional[str]] = mapped_column(Text)
    discovered_ids: Mapped[Optional[dict]] = mapped_column(JSONB)
    last_discovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    discovery_status: Mapped[Optional[str]] = mapped_column(Text)
    discovery_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="workspace_configs")
    notion_integration: Mapped["NotionIntegration"] = relationship(back_populates="workspace_config")


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        Index("ix_sync_runs_user_started", "user_id", "started_at"),
        Index(
            "ix_sync_runs_failed_pending",
            "status", "started_at",
            postgresql_where="status IN ('failed', 'pending')",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    sis_integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sis_integrations.id"), index=True)
    operation: Mapped[Optional[str]] = mapped_column(Text)
    triggered_by: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_type: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sync_runs")
    sis_integration: Mapped[Optional["SISIntegration"]] = relationship(back_populates="sync_runs")
