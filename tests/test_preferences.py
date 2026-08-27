import importlib
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database.models import Base, User, UserPreferences
from backend.db.database import get_db
from backend.main import app
from backend.services.preferences_service import (
    get_or_create_user,
    get_preferences,
    save_preferences,
)

migration_002 = importlib.import_module("backend.db.migrations.002_add_user_preferences")
migration_upgrade = migration_002.upgrade
migration_downgrade = migration_002.downgrade

# In-memory test database for isolated test execution
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)


def test_user_preferences_model_columns():
    """Step 1 Verification: UserPreferences model in backend/database/models.py has all required columns."""
    insp = inspect(UserPreferences)
    columns = {c.key: c for c in insp.columns}

    assert "user_id" in columns
    assert "spiral_threshold" in columns
    assert "negative_threshold" in columns
    assert "positive_threshold" in columns
    assert "toxicity_threshold" in columns
    assert "theme" in columns
    assert "updated_at" in columns

    # Test instantiation & to_dict()
    uid = uuid.uuid4()
    pref = UserPreferences(
        user_id=uid,
        spiral_threshold=0.75,
        negative_threshold=0.65,
        positive_threshold=0.55,
        toxicity_threshold=0.60,
        theme="dark",
    )
    data = pref.to_dict()
    assert data["user_id"] == str(uid)
    assert data["spiral_threshold"] == 0.75
    assert data["negative_threshold"] == 0.65
    assert data["positive_threshold"] == 0.55
    assert data["toxicity_threshold"] == 0.60
    assert data["theme"] == "dark"


def test_migration_002_add_user_preferences():
    """Step 2 Verification: Migration 002 upgrade and downgrade work on engine."""
    mig_engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    migration_upgrade(bind=mig_engine)

    insp = inspect(mig_engine)
    assert "user_preferences" in insp.get_table_names()
    cols = [c["name"] for c in insp.get_columns("user_preferences")]
    assert "spiral_threshold" in cols
    assert "negative_threshold" in cols
    assert "positive_threshold" in cols
    assert "toxicity_threshold" in cols
    assert "theme" in cols

    migration_downgrade(bind=mig_engine)
    insp_after = inspect(mig_engine)
    assert "user_preferences" not in insp_after.get_table_names()


def test_preferences_service_get_and_save():
    """Step 3 Verification: preferences_service get_preferences and save_preferences functions."""
    db = TestingSessionLocal()
    user_id = str(uuid.uuid4())

    # 1. get_preferences returns defaults if not present
    prefs = get_preferences(user_id=user_id, db=db)
    assert prefs is not None
    assert str(prefs.user_id) == user_id
    assert prefs.spiral_threshold == 0.7
    assert prefs.negative_threshold == 0.6
    assert prefs.positive_threshold == 0.5
    assert prefs.toxicity_threshold == 0.6
    assert prefs.theme == "light"

    # 2. save_preferences updates thresholds and theme
    updated = save_preferences(
        user_id=user_id,
        preferences={
            "spiral_threshold": 0.85,
            "negative_threshold": 0.70,
            "positive_threshold": 0.40,
            "toxicity_threshold": 0.55,
            "theme": "dark",
        },
        db=db,
    )
    assert updated.spiral_threshold == 0.85
    assert updated.negative_threshold == 0.70
    assert updated.positive_threshold == 0.40
    assert updated.toxicity_threshold == 0.55
    assert updated.theme == "dark"

    # 3. Subsequent get_preferences returns persisted values
    persisted = get_preferences(user_id=user_id, db=db)
    assert persisted.spiral_threshold == 0.85
    assert persisted.negative_threshold == 0.70
    assert persisted.positive_threshold == 0.40
    assert persisted.toxicity_threshold == 0.55
    assert persisted.theme == "dark"
    db.close()


def test_api_preferences_get_and_put():
    """Step 4 Verification: GET /v1/preferences and PUT /v1/preferences endpoints."""
    client = TestClient(app)
    test_user_id = str(uuid.uuid4())

    # 1. GET /v1/preferences returns default preferences
    res_get = client.get(f"/v1/preferences?user_id={test_user_id}")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert data_get["user_id"] == test_user_id
    assert data_get["spiral_threshold"] == 0.7
    assert data_get["negative_threshold"] == 0.6
    assert data_get["positive_threshold"] == 0.5
    assert data_get["toxicity_threshold"] == 0.6
    assert data_get["theme"] == "light"

    # 2. PUT /v1/preferences updates preferences
    payload = {
        "spiral_threshold": 0.90,
        "negative_threshold": 0.80,
        "positive_threshold": 0.35,
        "toxicity_threshold": 0.75,
        "theme": "dark",
    }
    res_put = client.put(f"/v1/preferences?user_id={test_user_id}", json=payload)
    assert res_put.status_code == 200
    data_put = res_put.json()
    assert data_put["spiral_threshold"] == 0.90
    assert data_put["negative_threshold"] == 0.80
    assert data_put["positive_threshold"] == 0.35
    assert data_put["toxicity_threshold"] == 0.75
    assert data_put["theme"] == "dark"

    # 3. GET /v1/preferences verifies PostgreSQL persistence
    res_verify = client.get(f"/v1/preferences?user_id={test_user_id}")
    assert res_verify.status_code == 200
    data_verify = res_verify.json()
    assert data_verify["spiral_threshold"] == 0.90
    assert data_verify["negative_threshold"] == 0.80
    assert data_verify["positive_threshold"] == 0.35
    assert data_verify["toxicity_threshold"] == 0.75
    assert data_verify["theme"] == "dark"


def test_api_preferences_me_backward_compatibility():
    """Compatibility check for /v1/preferences/me endpoints."""
    client = TestClient(app)
    test_user_id = str(uuid.uuid4())

    res_get = client.get(f"/v1/preferences/me?user_id={test_user_id}")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["active_profile"] == "balanced"

    res_post = client.post(
        f"/v1/preferences/me?user_id={test_user_id}",
        json={"active_profile": "calmer", "muted_sources": ["Toksik Kanal"]},
    )
    assert res_post.status_code == 200
    assert res_post.json()["active_profile"] == "calmer"
    assert res_post.json()["muted_sources"] == ["Toksik Kanal"]
