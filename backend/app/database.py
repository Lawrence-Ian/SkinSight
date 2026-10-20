"""SKINSIGHT v2 — Database"""

from datetime import datetime
import logging
import os
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    inspect,
    select,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "skinsight.db"


def _database_url():
    configured_url = os.getenv("DATABASE_URL")
    if not configured_url:
        return f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    if configured_url.startswith("postgres://"):
        return configured_url.replace("postgres://", "postgresql+psycopg://", 1)
    if configured_url.startswith("postgresql://"):
        return configured_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return configured_url


DATABASE_URL = _database_url()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    scan_history = relationship(
        "ScanHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    routine_progress = relationship(
        "RoutineProgress",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    skin_type = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class ScanHistory(Base):
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    condition = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    all_predictions = Column(Text, nullable=False)
    source = Column(String(30), default="live_camera")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="scan_history")
    recommendations = relationship(
        "Recommendation",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
    routine_progress = relationship(
        "RoutineProgress",
        back_populates="scan",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RoutineProgress(Base):
    __tablename__ = "routine_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "scan_id", name="uq_routine_progress_user_scan"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id = Column(
        Integer,
        ForeignKey("scan_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed_steps = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="routine_progress")
    scan = relationship("ScanHistory", back_populates="routine_progress")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(150), nullable=True)
    category = Column(String(80), nullable=True)
    description = Column(Text, nullable=True)
    ingredients = Column(Text, nullable=True)
    skin_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    recommendations = relationship(
        "Recommendation",
        back_populates="product",
        cascade="all, delete-orphan",
    )
class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(
        Integer,
        ForeignKey("scan_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recommendation_reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("ScanHistory", back_populates="recommendations")
    product = relationship("Product", back_populates="recommendations")


def init_db():
    drop_empty_unused_tables()
    Base.metadata.create_all(bind=engine)
    drop_removed_scan_columns()
    drop_removed_profile_columns()
    db = SessionLocal()
    try:
        ensure_user_data(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def drop_removed_scan_columns(bind=engine):
    if bind.dialect.name != "sqlite":
        return

    with bind.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("scan_history")
        }
        if "has_lesion_alert" in columns:
            connection.exec_driver_sql(
                "ALTER TABLE scan_history DROP COLUMN has_lesion_alert"
            )


def drop_removed_profile_columns(bind=engine):
    if bind.dialect.name != "sqlite":
        return

    removed_columns = {
        "skin_concerns",
        "sensitivity_level",
        "goals",
        "allergies",
    }
    with bind.begin() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("user_profiles")
        }
        for column in removed_columns.intersection(columns):
            connection.exec_driver_sql(
                f"ALTER TABLE user_profiles DROP COLUMN {column}"
            )


def drop_empty_unused_tables(bind=engine):
    legacy_tables = ("favorite_products", "location_favorites")
    with bind.begin() as connection:
        inspector = inspect(connection)
        for table_name in legacy_tables:
            if not inspector.has_table(table_name):
                continue
            table = Table(table_name, MetaData(), autoload_with=connection)
            count_result = connection.execute(select(func.count()).select_from(table))
            row_count = count_result.scalar_one()
            count_result.close()
            if row_count:
                logging.getLogger(__name__).warning(
                    "Keeping unused legacy table %s because it contains %s rows.",
                    table_name,
                    row_count,
                )
                continue
            table.drop(connection)


def persist_scan_recommendations(db, scan, condition, products):
    for recommended_product in products:
        product = db.query(Product).filter(
            Product.name == recommended_product["name"],
            Product.brand == recommended_product.get("brand"),
        ).first()
        if product is None:
            product = Product(
                name=recommended_product["name"],
                brand=recommended_product.get("brand"),
                description=recommended_product.get("purpose"),
                ingredients=recommended_product.get("ingredient"),
                skin_type=condition,
            )
            db.add(product)
            db.flush()

        db.add(Recommendation(
            scan_id=scan.id,
            product_id=product.id,
            recommendation_reason=recommended_product.get(
                "dermatologist_recommendation",
                recommended_product.get("purpose", ""),
            ),
        ))


def ensure_user_data(db):
    from app.services.recommendations import get_recommendation

    missing_profiles = db.query(User.id).outerjoin(
        UserProfile,
        UserProfile.user_id == User.id,
    ).filter(UserProfile.id.is_(None)).all()
    db.add_all(UserProfile(user_id=user_id) for (user_id,) in missing_profiles)

    for user in db.query(User).all():
        profile = db.query(UserProfile).filter_by(user_id=user.id).first()
        latest_scan = db.query(ScanHistory).filter_by(user_id=user.id).order_by(
            ScanHistory.created_at.desc()
        ).first()
        if profile and profile.skin_type is None and latest_scan:
            profile.skin_type = latest_scan.condition

    legacy_scans = db.query(ScanHistory).filter(~ScanHistory.recommendations.any()).all()
    for scan in legacy_scans:
        recommendation = get_recommendation(scan.condition)
        persist_scan_recommendations(db, scan, scan.condition, recommendation["products"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
