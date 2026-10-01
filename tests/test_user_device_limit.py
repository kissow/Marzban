from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db import crud
from app.db.models import User
from app.models.user import DeviceLimitAction


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def make_user(db, limit=0, action=DeviceLimitAction.log_only):
    user = User(
        username="device_test_user",
        device_limit=limit,
        device_limit_action=action,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_same_public_ip_counts_distinct_hwid_and_same_hwid_does_not_duplicate(db):
    user = make_user(db, limit=10, action=DeviceLimitAction.reject_new)

    results = [
        crud.register_user_device(db, user, f"device-{index}", client_ip="198.51.100.10")
        for index in range(10)
    ]
    assert all(item["accepted"] for item in results)
    assert results[-1]["registered_devices"] == 10

    duplicate = crud.register_user_device(db, user, "device-0", client_ip="203.0.113.4")
    assert duplicate["accepted"] is True
    assert duplicate["is_new_device"] is False
    assert duplicate["registered_devices"] == 10

    rejected = crud.register_user_device(db, user, "device-10", client_ip="198.51.100.10")
    assert rejected["accepted"] is False
    assert rejected["is_new_device"] is True
    assert crud.get_user_device_status(db, user)["registered_devices"] == 10


def test_status_does_not_expose_hwid_and_reports_remaining_slots(db):
    user = make_user(db, limit=3, action=DeviceLimitAction.reject_new)
    crud.register_user_device(db, user, "device-a", client_ip="203.0.113.10")

    status = crud.get_user_device_status(db, user)

    assert status == {
        "device_limit": 3,
        "registered_devices": 1,
        "remaining_devices": 2,
        "device_limit_mode": "hwid",
        "device_limit_action": "reject_new",
        "hwid_supported": True,
        "enforcement_scope": "subscription_requests_with_hwid",
    }
    assert all("hwid" not in key.lower() or key == "hwid_supported" for key in status)


def test_log_only_records_over_limit_without_rejecting(db):
    user = make_user(db, limit=2, action=DeviceLimitAction.log_only)

    results = [crud.register_user_device(db, user, f"device-{index}") for index in range(3)]

    assert all(item["accepted"] for item in results)
    assert results[-1]["remaining_devices"] == 0
    assert crud.get_user_device_status(db, user)["registered_devices"] == 3


def test_hwid_is_hashed_and_user_delete_cascades_devices(db):
    user = make_user(db, limit=0)
    crud.register_user_device(db, user, "secret-hardware-id", client_ip="192.0.2.10")

    stored = user.devices[0]
    assert stored.hwid_hash != "secret-hardware-id"
    assert len(stored.hwid_hash) == 64

    crud.remove_user(db, user)
    assert db.query(type(stored)).count() == 0


def test_revoked_hwid_can_be_registered_again_and_counts_as_active(db):
    user = make_user(db, limit=1, action=DeviceLimitAction.reject_new)
    crud.register_user_device(db, user, "reusable-device")

    device = user.devices[0]
    device.revoked_at = datetime.utcnow()
    db.commit()

    restored = crud.register_user_device(db, user, "reusable-device")

    assert restored["accepted"] is True
    assert restored["is_new_device"] is True
    assert restored["registered_devices"] == 1
