"""回归：库结论 -> 列表展示 -> 详情文字 全链路一致，权限与边界值。"""
import time
import uuid

import pytest

from rules import LIMIT_MM, judge
from models import row_dict

try:
    import api as api_module

    _import_error = None
except Exception as exc:  # 数据库不可达等场景下跳过接口级用例
    api_module = None
    _import_error = exc

needs_db = pytest.mark.skipif(
    api_module is None, reason=f"接口或数据库不可用：{_import_error}"
)


def _client():
    return api_module.app.test_client()


def _login(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": "Bearer " + res.get_json()["access_token"]}


def _wait_done(client, headers, row_id, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = client.get("/api/logs", headers=headers)
        assert res.status_code == 200
        for row in res.get_json():
            if row["id"] == row_id and row["status"] == "done":
                return row
        time.sleep(0.3)
    pytest.fail(f"行 {row_id} 在 {timeout}s 内未被认领处理")


def _submit_and_wait(delta_mm):
    client = _client()
    headers = _login(client, "surveyor", "surv123456")
    chainage = f"T-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/logs", json={"chainage": chainage, "delta_mm": delta_mm}, headers=headers
    )
    assert res.status_code == 201, res.get_json()
    return _wait_done(client, headers, res.get_json()["id"])


# ---------- 纯逻辑：判定边界（拱顶够线不得被写成超限） ----------

def test_judge_at_limit_is_pass():
    assert judge(LIMIT_MM)[0] == "合格"
    assert judge(-LIMIT_MM)[0] == "合格"


def test_judge_beyond_limit_is_fail():
    assert judge(LIMIT_MM + 0.1)[0] == "超限"
    assert judge(-LIMIT_MM - 0.1)[0] == "超限"


def test_row_dict_keeps_verdict_and_reason():
    class Row:
        id, chainage, delta_mm, status = 1, "K12+180", 1.2, "done"
        verdict, reason = "合格", "收敛 1.2 mm 在 ±3.0 mm 以内"
        created_by = "surveyor"
        created_at = processed_at = None

    d = row_dict(Row())
    assert d["verdict"] == "合格"
    assert d["reason"] == "收敛 1.2 mm 在 ±3.0 mm 以内"
    assert "tone" not in d


# ---------- 权限：巡检员禁写，可写账号仍能交单 ----------

@needs_db
def test_inspector_cannot_submit():
    client = _client()
    headers = _login(client, "inspector", "insp123456")
    res = client.post("/api/logs", json={"chainage": "K99+999", "delta_mm": 1.0}, headers=headers)
    assert res.status_code == 403


@needs_db
def test_surveyor_can_submit():
    client = _client()
    headers = _login(client, "surveyor", "surv123456")
    chainage = f"T-{uuid.uuid4().hex[:8]}"
    res = client.post("/api/logs", json={"chainage": chainage, "delta_mm": 0.8}, headers=headers)
    assert res.status_code == 201
    body = res.get_json()
    assert body["chainage"] == chainage
    assert body["status"] == "pending"


# ---------- 展示忠实于库：合格不被粉饰为超限，详情文字对得上 ----------

@needs_db
def test_seed_rows_shown_faithfully():
    client = _client()
    headers = _login(client, "inspector", "insp123456")
    res = client.get("/api/logs", headers=headers)
    assert res.status_code == 200
    rows = {r["chainage"]: r for r in res.get_json()}

    passed = rows["K12+180"]
    assert passed["verdict"] == "合格"
    assert "超限" not in passed["reason"]
    assert "以内" in passed["reason"]
    assert "tone" not in passed

    failed = rows["K18+040"]
    assert failed["verdict"] == "超限"
    assert "超过" in failed["reason"]


@needs_db
def test_new_pass_row_not_polished():
    row = _submit_and_wait(2.4)
    verdict, reason = judge(2.4)
    assert verdict == "合格"
    assert row["verdict"] == verdict
    assert row["reason"] == reason
    assert "tone" not in row


@needs_db
def test_boundary_reading_is_pass_not_fail():
    row = _submit_and_wait(LIMIT_MM)
    assert row["verdict"] == "合格"
    assert "超限" not in row["reason"]


@needs_db
def test_over_limit_reading_is_fail():
    row = _submit_and_wait(LIMIT_MM + 0.1)
    assert row["verdict"] == "超限"
    assert "超过" in row["reason"]
