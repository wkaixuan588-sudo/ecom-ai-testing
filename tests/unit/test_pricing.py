# -*- coding: utf-8 -*-
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.pricing import (
    subtotal, book_promotion, member_discount_rate, calculate_order_total,
)


# ---------- subtotal ----------

def test_subtotal_basic():
    """等价类（有效输入）：多商品小计 = Σ(price × qty)"""
    items = [
        {"price": 10.0, "qty": 2, "sku_type": "book"},
        {"price": 5.5, "qty": 4, "sku_type": "food"},
    ]
    assert subtotal(items) == 42.0


def test_subtotal_single_item():
    """等价类（有效输入）：单商品小计"""
    assert subtotal([{"price": 7.25, "qty": 3, "sku_type": "book"}]) == 21.75


def test_subtotal_empty_items():
    """异常输入（空）：空订单小计为 0"""
    assert subtotal([]) == 0


# ---------- book_promotion ----------

def test_book_promotion_above_threshold():
    """等价类（有效输入）：书籍小计 > 100，减免 10"""
    items = [{"price": 55.0, "qty": 2, "sku_type": "book"}]
    assert book_promotion(items) == 10.0


def test_book_promotion_exactly_100():
    """边界值：书籍小计恰好 = 100（"满100元"含100），应减免 10"""
    items = [{"price": 50.0, "qty": 2, "sku_type": "book"}]
    assert book_promotion(items) == 10.0


def test_book_promotion_just_below_100():
    """边界值：书籍小计 = 99.99（略低于阈值），不减免"""
    items = [{"price": 49.995, "qty": 2, "sku_type": "book"}]
    assert book_promotion(items) == 0.0


def test_book_promotion_mixed_types_only_book_counts():
    """等价类：非 book 品类不参与书籍满减"""
    items = [
        {"price": 60.0, "qty": 1, "sku_type": "book"},
        {"price": 100.0, "qty": 1, "sku_type": "electronics"},
    ]
    assert book_promotion(items) == 0.0


def test_book_promotion_no_books():
    """等价类：无书籍商品，减免 0"""
    items = [{"price": 200.0, "qty": 1, "sku_type": "food"}]
    assert book_promotion(items) == 0.0


def test_book_promotion_empty():
    """异常输入（空）：空列表减免 0"""
    assert book_promotion([]) == 0.0


# ---------- member_discount_rate ----------

def test_member_rate_normal():
    """等价类：normal 无折扣，rate = 1.0"""
    assert member_discount_rate("normal") == 1.0


def test_member_rate_silver():
    """等价类：silver 95 折，rate = 0.95"""
    assert member_discount_rate("silver") == 0.95


def test_member_rate_gold():
    """等价类：gold 9 折，rate = 0.90"""
    assert member_discount_rate("gold") == 0.90


def test_member_rate_unknown_level():
    """异常输入（非法值）：未知会员等级应抛 ValueError"""
    import pytest
    with pytest.raises(ValueError):
        member_discount_rate("platinum")


# ---------- calculate_order_total ----------

def test_total_basic_normal_no_promo():
    """等价类：普通会员、无满减，总额 = 小计，两位小数"""
    items = [{"price": 33.33, "qty": 1, "sku_type": "food"}]
    assert calculate_order_total(items, "normal") == 33.33


def test_total_gold_with_book_promo_two_decimals():
    """需求规则4（精度）：结果必须保留两位小数。
    100 * 0.95 的浮点噪声 95.00000000000001 不可接受。"""
    items = [{"price": 50.0, "qty": 2, "sku_type": "book"}]
    result = calculate_order_total(items, "silver")
    assert round(result, 2) == result  # 不存在第三位小数的噪声


def test_total_gold_book_promo_value():
    """等价类：gold 会员 + 书籍满 100 减 10：(100 - 10) × 0.9 = 81.00"""
    items = [{"price": 50.0, "qty": 2, "sku_type": "book"}]
    assert calculate_order_total(items, "gold") == 81.00


def test_total_result_rounded_half_up():
    """需求规则4（精度）：第三位小数按 ROUND_HALF_UP 保留两位。
    3 件 10.005 元：小计 30.015 → 30.02（普通会员）"""
    items = [{"price": 10.005, "qty": 3, "sku_type": "food"}]
    assert calculate_order_total(items, "normal") == 30.02


def test_total_empty_items():
    """异常输入（空）：空订单总额为 0"""
    assert calculate_order_total([], "normal") == 0


def test_total_silver_precision():
    """需求规则4（精度）：silver 95 折结果保留两位小数。
    小计 21.00 → 21.00 × 0.95 = 19.95，不允许浮点噪声。"""
    items = [{"price": 21.0, "qty": 1, "sku_type": "food"}]
    assert calculate_order_total(items, "silver") == 19.95
