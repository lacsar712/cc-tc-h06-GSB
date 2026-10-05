"""接口层：列表结论与库一致（不再被展示层粉饰）、权限边界、认领判定。"""
import time

import pytest

import api as api_mod
from api import app
from models import ConvergenceLog, SessionLocal
from claimer import claim_once


@pytest.fixture()
def client():
    app.testing = True
    return app.test_client()


def login(client, username, password):
    res = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert res.status_code == 200
    return res.get_json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_seed_list_not_polished(client):
    """合格行必须原样返回合格，超限行保持超限，详情文字与结论一致。"""
    token = login(client, "inspector", "insp123456")
    res = client.get("/api/logs", headers=auth(token))
    assert res.status_code == 200
    rows = {r["chainage"]: r for r in res.get_json()}

    good = rows["K12+180"]
    assert good["verdict"] == "合格"
    assert good["status"] == "done"
    assert "以内" in good["reason"]
    assert "展示层粉饰" not in good["reason"]
    assert "tone" not in good

    bad = rows["K18+040"]
    assert bad["verdict"] == "超限"
    assert "超过" in bad["reason"]


def test_inspector_cannot_submit(client):
    """巡检员只读：POST 被 403 拒绝。"""
    token = login(client, "inspector", "insp123456")
    res = client.post(
        "/api/logs",
        headers=auth(token),
        json={"chainage": "K30+000", "delta_mm": 1.0},
    )
    assert res.status_code == 403


def test_surveyor_can_submit_pending(client):
    """可写账号能交新的测缝单，进入待认领。"""
    token = login(client, "surveyor", "surv123456")
    res = client.post(
        "/api/logs",
        headers=auth(token),
        json={"chainage": "K30+010", "delta_mm": 2.4},
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["status"] == "pending"
    assert body["verdict"] is None
    assert body["created_by"] == "surveyor"


def _latest_id():
    db = SessionLocal()
    try:
        return db.query(ConvergenceLog).order_by(ConvergenceLog.id.desc()).first().id
    finally:
        db.close()


def test_claim_judges_boundary_as_pass(client):
    """够线（3.0 mm）经认领后必须是合格，不是超限。"""
    token = login(client, "surveyor", "surv123456")
    created = client.post(
        "/api/logs",
        headers=auth(token),
        json={"chainage": "K31+000", "delta_mm": 3.0},
    ).get_json()

    # 主动走一遍认领逻辑（与后台线程同一路径），避免依赖线程时序
    assert claim_once() is True
    # 若后台线程抢先处理，再调用应返回 False
    deadline = time.time() + 3
    db = SessionLocal()
    try:
        row = db.get(ConvergenceLog, created["id"])
        while row.status != "done" and time.time() < deadline:
            db.rollback()
            time.sleep(0.05)
            row = db.get(ConvergenceLog, created["id"])
        assert row.status == "done"
        assert row.verdict == "合格"
        assert "以内" in row.reason
    finally:
        db.close()


def test_claim_judges_over_limit_as_fail(client):
    token = login(client, "surveyor", "surv123456")
    created = client.post(
        "/api/logs",
        headers=auth(token),
        json={"chainage": "K31+010", "delta_mm": 5.6},
    ).get_json()
    claim_once()
    db = SessionLocal()
    try:
        deadline = time.time() + 3
        row = db.get(ConvergenceLog, created["id"])
        while row.status != "done" and time.time() < deadline:
            db.rollback()
            time.sleep(0.05)
            row = db.get(ConvergenceLog, created["id"])
        assert row.verdict == "超限"
        assert "超过" in row.reason
    finally:
        db.close()
