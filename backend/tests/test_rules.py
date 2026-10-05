"""判定规则边界：±3.0 mm 为合格（含等号），超出才是超限。"""
from rules import LIMIT_MM, judge


def test_zero_is_pass():
    verdict, reason = judge(0.0)
    assert verdict == "合格"
    assert "以内" in reason


def test_boundary_positive_inclusive_is_pass():
    # 拱顶够线：恰好在 3.0 mm 线上不得被写成超限
    verdict, reason = judge(LIMIT_MM)
    assert verdict == "合格"
    assert "以内" in reason


def test_boundary_negative_inclusive_is_pass():
    verdict, reason = judge(-LIMIT_MM)
    assert verdict == "合格"
    assert "以内" in reason


def test_just_over_positive_is_fail():
    verdict, reason = judge(LIMIT_MM + 0.0001)
    assert verdict == "超限"
    assert "超过" in reason


def test_over_negative_is_fail():
    verdict, reason = judge(-3.1)
    assert verdict == "超限"
    assert "超过" in reason


def test_seed_expectations_hold():
    assert judge(1.2)[0] == "合格"
    assert judge(5.6)[0] == "超限"
