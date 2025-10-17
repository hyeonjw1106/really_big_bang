from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Float, ForeignKey, Text

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