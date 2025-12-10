from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Float, ForeignKey, Text, DateTime, Integer, JSON, func

class Base(DeclarativeBase): pass

class Epoch(Base):
    __tablename__ = "epochs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    start_norm: Mapped[float] = mapped_column(Float)  # 0~1 정규화
    end_norm: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="epoch", cascade="all, delete-orphan")

class Annotation(Base):
    __tablename__ = "annotations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    epoch_id: Mapped[int] = mapped_column(ForeignKey("epochs.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    time_mark: Mapped[float] = mapped_column(Float)
    epoch: Mapped[Epoch] = relationship(back_populates="annotations")

class Element(Base):
    __tablename__ = "elements"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    type: Mapped[str] = mapped_column(String(40))      # quark/atom/star...
    description: Mapped[str | None] = mapped_column(Text)
    charge_range: Mapped[str | None] = mapped_column(String(40))
    mass_gev: Mapped[float | None] = mapped_column(Float)
    genesis_time: Mapped[str | None] = mapped_column(String(60))

class SceneFile(Base):
    __tablename__ = "scene_files"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(255), unique=True)
    file_size: Mapped[int | None] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    render_jobs: Mapped[list["RenderJob"]] = relationship(back_populates="scene", cascade="all, delete-orphan")

class RenderJob(Base):
    __tablename__ = "render_jobs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scene_files.id", ondelete="CASCADE"), index=True)
    epoch_id: Mapped[int | None] = mapped_column(ForeignKey("epochs.id", ondelete="SET NULL"), nullable=True, index=True)
    time_norm: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    message: Mapped[str | None] = mapped_column(Text)
    output_path: Mapped[str | None] = mapped_column(String(255))
    params: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    scene: Mapped[SceneFile] = relationship(back_populates="render_jobs")


class CosmicEvent(Base):
    __tablename__ = "cosmic_events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    time_range: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(80))
    time_norm: Mapped[float] = mapped_column(Float, index=True)
    media_url: Mapped[str | None] = mapped_column(String(255))
    epoch_id: Mapped[int | None] = mapped_column(ForeignKey("epochs.id", ondelete="SET NULL"), nullable=True, index=True)
    default_scene_id: Mapped[int | None] = mapped_column(ForeignKey("scene_files.id", ondelete="SET NULL"), nullable=True)
