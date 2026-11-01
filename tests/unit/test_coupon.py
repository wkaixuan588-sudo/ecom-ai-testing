# -*- coding: utf-8 -*-
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from datetime import datetime
import pytest
from app.coupon import apply_coupon


VF = datetime(2026, 1, 1, 0, 0, 0)
VT = datetime(2026, 1, 31, 0, 0, 0)


def full_coupon(threshold=100.0, amount=20.0, vf=VF, vt=VT):
    return {"type": "full_reduction", "threshold": threshold, "amount": amount,
            "valid_from": vf, "valid_to": vt}


def disc_coupon(rate=0.9, cap=None, vf=VF, vt=VT):
    c = {"type": "discount", "rate": rate, "valid_from": vf, "valid_to": vt}
    if cap is not None:
        c["cap"] = cap
    return c


# ---------- 满减券 ----------

def test_full_reduction_qualified():
    """等价类（有效输入）：金额 >= threshold，减免 amount"""
    assert apply_coupon(150.0, full_coupon(), now=datetime(2026, 1, 10)) == 20.0


def test_full_reduction_exactly_threshold():
    """边界值：订单金额恰好 = threshold（"满 threshold"含等于），应减免"""
    assert apply_coupon(100.0, full_coupon(), now=datetime(2026, 1, 10)) == 20.0


def test_full_reduction_below_threshold():
    """边界值：订单金额 99.99（略低于 threshold），不减免"""
    assert apply_coupon(99.99, full_coupon(), now=datetime(2026, 1, 10)) == 0.0


# ---------- 折扣券 ----------

def test_discount_basic():
    """等价类（有效输入）：9 折券优惠 = amount × (1 - rate)"""
    assert apply_coupon(200.0, disc_coupon(rate=0.9), now=datetime(2026, 1, 10)) == pytest.approx(20.0)


def test_discount_capped():
    """等价类：优惠超过封顶 cap 时取 cap"""
    assert apply_coupon(500.0, disc_coupon(rate=0.5, cap=100.0),
                        now=datetime(2026, 1, 10)) == 100.0


def test_discount_not_capped():
    """等价类：优惠低于封顶时不封顶"""
    assert apply_coupon(100.0, disc_coupon(rate=0.9, cap=100.0),
                        now=datetime(2026, 1, 10)) == pytest.approx(10.0)


# ---------- 有效期（闭区间） ----------

def test_valid_on_valid_from_boundary():
    """边界值：生效日当天 valid_from 整点应可用（闭区间左端点）"""
    assert apply_coupon(150.0, full_coupon(), now=VF) == 20.0


def test_valid_on_valid_to_boundary():
    """边界值：到期日当天 valid_to 整点应仍可使用（闭区间右端点，需求 v1.2）"""
    assert apply_coupon(150.0, full_coupon(), now=VT) == 20.0


def test_invalid_before_valid_from():
    """边界值：早于 valid_from 不可用"""
    assert apply_coupon(150.0, full_coupon(),
                        now=datetime(2025, 12, 31, 23, 59, 59)) == 0.0


def test_invalid_after_valid_to():
    """边界值：晚于 valid_to 不可用"""
    assert apply_coupon(150.0, full_coupon(),
                        now=datetime(2026, 1, 31, 0, 0, 1)) == 0.0


def test_valid_inside_window():
    """等价类：有效期中间时间点可用"""
    assert apply_coupon(150.0, full_coupon(), now=datetime(2026, 1, 15, 12, 0)) == 20.0


# ---------- 订单金额校验（需求：必须为正数） ----------

def test_negative_amount_rejected():
    """异常输入（负数）：订单金额为负时优惠必须为 0（折扣券不得算出负优惠/反向加钱）"""
    assert apply_coupon(-50.0, disc_coupon(rate=0.9), now=datetime(2026, 1, 10)) == 0.0


def test_negative_amount_full_reduction_rejected():
    """异常输入（负数）：负金额 + 满减券（低门槛）也必须返回 0"""
    assert apply_coupon(-50.0, full_coupon(threshold=-100.0),
                        now=datetime(2026, 1, 10)) == 0.0


def test_zero_amount_rejected():
    """异常输入（0）：订单金额为 0 不是正数，优惠为 0"""
    assert apply_coupon(0.0, full_coupon(), now=datetime(2026, 1, 10)) == 0.0


# ---------- 券本身异常 ----------

def test_none_coupon():
    """异常输入（空）：coupon 为 None 返回 0"""
    assert apply_coupon(100.0, None, now=datetime(2026, 1, 10)) == 0.0


def test_unknown_coupon_type():
    """异常输入（非法值）：未知券类型返回 0"""
    c = {"type": "mystery", "valid_from": VF, "valid_to": VT}
    assert apply_coupon(100.0, c, now=datetime(2026, 1, 10)) == 0.0
