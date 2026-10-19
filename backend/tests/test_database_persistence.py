import asyncio
import base64
import json
import sys
from pathlib import Path

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import database
from app.api import analysis, auth, chat, history
from app.api.dependencies import require_user
from app.services.auth_service import create_token
from app.services.recommendations import get_recommendation


def make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    database.Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_scan_saves_history_and_recommended_products(tmp_path, monkeypatch):
    db = make_session(tmp_path)
    user = database.User(
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    class Predictor:
        def predict(self, image_bytes):
            return {
                "condition": "dry",
                "confidence": 0.9,
                "all_scores": {"dry": 0.9, "oily": 0.1},
                "using_mock": False,
                "error": None,
            }

    monkeypatch.setattr(analysis, "get_predictor", lambda: Predictor())
    body = analysis.LiveScanRequest(frame=base64.b64encode(b"x" * 4096).decode())
    response = asyncio.run(analysis.scan_live_frame(body, {"user_id": user.id}, db))
    payload = json.loads(response.body)

    scan = db.query(database.ScanHistory).filter_by(id=payload["scan_id"]).one()
    saved_recommendations = db.query(database.Recommendation).filter_by(scan_id=scan.id).all()
    assert scan.user_id == user.id
    assert json.loads(scan.all_predictions) == {"dry": 0.9, "oily": 0.1}
    assert len(saved_recommendations) == len(payload["products"])
    assert all(item.product_id is not None for item in saved_recommendations)
    assert db.query(database.Product).count() == len(payload["products"])
    restored_response = asyncio.run(history.get_scan(scan.id, {"user_id": user.id}, db))
    restored = json.loads(restored_response.body)
    assert {item["name"] for item in restored["products"]} == {
        item["name"] for item in payload["products"]
    }
    assert all("brand" not in item for item in payload["products"])
    assert all(item["price_range"] for item in payload["products"])
    assert all("brand" not in item for item in restored["products"])
    db.close()


def test_recommendations_are_single_budget_friendly_products():
    for recommendation in (
        get_recommendation("acne"),
        get_recommendation("oily"),
        get_recommendation("dry"),
        get_recommendation("normal"),
    ):
        assert len(recommendation["products"]) == 1
        product = recommendation["products"][0]
        assert "brand" not in product
        assert product["price_range"].startswith("₱100")


def test_oily_skin_does_not_recommend_moisturizer():
    recommendation = get_recommendation("oily")
    routine_text = " ".join(recommendation["morning_routine"] + recommendation["night_routine"])
    product_text = " ".join(product["name"] for product in recommendation["products"])
    assert "moisturizer" not in f"{routine_text} {product_text}".lower()


def test_scan_does_not_return_success_when_persistence_fails(tmp_path, monkeypatch):
    db = make_session(tmp_path)
    user = database.User(
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    class Predictor:
        def predict(self, image_bytes):
            return {
                "condition": "dry",
                "confidence": 0.9,
                "all_scores": {"dry": 0.9},
                "using_mock": False,
                "error": None,
            }

    monkeypatch.setattr(analysis, "get_predictor", lambda: Predictor())
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")))
    body = analysis.LiveScanRequest(frame=base64.b64encode(b"x" * 4096).decode())

    try:
        asyncio.run(analysis.scan_live_frame(body, {"user_id": user.id}, db))
        assert False, "scan should fail when persistence fails"
    except HTTPException as error:
        assert error.status_code == 500
        assert db.query(database.ScanHistory).count() == 0
        assert db.query(database.Product).count() == 0
    finally:
        db.close()


def test_profile_and_chat_are_saved_per_user(tmp_path, monkeypatch):
    db = make_session(tmp_path)
    signup_response = asyncio.run(auth.signup(
        auth.SignupRequest(name="Test User", email="test@example.com", password="secure-pass"),
        db,
    ))
    account_data = json.loads(signup_response.body)
    user_id = account_data["user"]["id"]
    assert db.query(database.UserProfile).filter_by(user_id=user_id).one()

    profile = auth.ProfileUpdate(
        skin_type="dry",
    )
    asyncio.run(auth.update_profile(profile, {"user_id": user_id}, db))
    account = asyncio.run(auth.get_account({"user_id": user_id}, db))
    assert account["profile"] == profile.model_dump()

    monkeypatch.setattr(chat, "get_bot_response", lambda message: {
        "response": f"Answer: {message}",
        "category": "general",
    })
    response = asyncio.run(chat.chat(
        chat.ChatRequest(message="What is a gentle cleanser?"),
        {"user_id": user_id},
        db,
    ))
    session_id = json.loads(response.body)["session_id"]
    stored_chat = asyncio.run(chat.get_session(session_id, {"user_id": user_id}, db))
    assert [message["sender"] for message in stored_chat["messages"]] == ["user", "assistant"]
    assert stored_chat["messages"][0]["content"] == "What is a gentle cleanser?"
    assert db.query(database.ChatSession).filter_by(user_id=user_id).count() == 1
    deleted = asyncio.run(chat.delete_session(session_id, {"user_id": user_id}, db))
    assert deleted["session_id"] == session_id
    assert db.query(database.ChatSession).filter_by(id=session_id).count() == 0
    assert db.query(database.ChatMessage).filter_by(session_id=session_id).count() == 0
    db.close()


def test_routine_progress_is_saved_and_scoped_to_scan_owner(tmp_path):
    db = make_session(tmp_path)
    user = database.User(
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password-hash",
    )
    other_user = database.User(
        name="Other User",
        email="other@example.com",
        password_hash="not-a-real-password-hash",
    )
    db.add_all([user, other_user])
    db.commit()
    scan = database.ScanHistory(
        user_id=user.id,
        condition="dry",
        confidence=0.9,
        all_predictions="{}",
    )
    db.add(scan)
    db.commit()

    progress = history.RoutineProgressUpdate(morning=[0], night=[1])
    asyncio.run(history.save_routine_progress(scan.id, progress, {"user_id": user.id}, db))
    restored = asyncio.run(history.get_routine_progress(scan.id, {"user_id": user.id}, db))
    assert restored["progress"] == {"morning": [0], "night": [1]}
    assert db.query(database.RoutineProgress).filter_by(user_id=user.id, scan_id=scan.id).count() == 1

    try:
        asyncio.run(history.get_routine_progress(scan.id, {"user_id": other_user.id}, db))
        assert False, "another user must not read this scan's progress"
    except HTTPException as error:
        assert error.status_code == 404
    db.close()


def test_startup_backfill_adds_missing_data_only_once(tmp_path):
    db = make_session(tmp_path)
    user = database.User(
        name="Legacy User",
        email="legacy@example.com",
        password_hash="not-a-real-password-hash",
    )
    db.add(user)
    db.flush()
    scan = database.ScanHistory(
        user_id=user.id,
        condition="oily",
        confidence=0.8,
        all_predictions='{"oily": 0.8}',
    )
    db.add(scan)
    db.commit()

    database.ensure_user_data(db)
    db.commit()
    database.ensure_user_data(db)
    db.commit()

    assert db.query(database.UserProfile).filter_by(user_id=user.id).count() == 1
    assert db.query(database.Recommendation).filter_by(scan_id=scan.id).count() == len(
        get_recommendation("oily")["products"]
    )
    db.close()


def test_user_dependency_rejects_missing_or_deleted_accounts(tmp_path):
    db = make_session(tmp_path)
    user = database.User(
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    with pytest.raises(HTTPException) as missing_auth:
        require_user(None, db)
    assert missing_auth.value.status_code == 401
    assert require_user(f"Bearer {create_token(user.id, user.email)}", db)["user_id"] == user.id

    db.delete(user)
    db.commit()
    with pytest.raises(HTTPException) as deleted_account:
        require_user(f"Bearer {create_token(user.id, user.email)}", db)
    assert deleted_account.value.status_code == 401
    db.close()


def test_cleanup_drops_only_empty_unused_tables(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE favorite_products (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE location_favorites (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("INSERT INTO location_favorites (id) VALUES (1)")

    database.drop_empty_unused_tables(engine)

    table_names = set(database.inspect(engine).get_table_names())
    assert "favorite_products" not in table_names
    assert "location_favorites" in table_names
    engine.dispose()


def test_removed_lesion_alert_column_is_migrated(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE scan_history ("
            "id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
            "condition VARCHAR(50) NOT NULL, confidence FLOAT NOT NULL, "
            "all_predictions TEXT NOT NULL, has_lesion_alert BOOLEAN, "
            "source VARCHAR(30), created_at DATETIME)"
        )

    database.drop_removed_scan_columns(engine)

    columns = {column["name"] for column in database.inspect(engine).get_columns("scan_history")}
    assert "has_lesion_alert" not in columns
    engine.dispose()


def test_removed_profile_columns_are_migrated(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-profile.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE user_profiles ("
            "id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
            "skin_type VARCHAR(50), skin_concerns TEXT, "
            "sensitivity_level VARCHAR(30), goals TEXT, allergies TEXT, "
            "updated_at DATETIME)"
        )

    database.drop_removed_profile_columns(engine)

    columns = {column["name"] for column in database.inspect(engine).get_columns("user_profiles")}
    assert columns == {"id", "user_id", "skin_type", "updated_at"}
    engine.dispose()