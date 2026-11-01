# -*- coding: utf-8 -*-
"""计价引擎：订单金额计算 + 会员折扣 + 品类满减。

业务规则（需求文档 v1.2）：
1. 订单小计 = Σ(price × qty)
2. 会员折扣：normal 无折扣；silver 95 折；gold 9 折
3. 品类活动：书籍类（sku_type="book"）小计满 100 元立减 10 元
4. 所有金额计算结果必须保留两位小数（对客展示一致性要求）
"""
from decimal import Decimal, ROUND_HALF_UP

MEMBER_DISCOUNT = {"normal": 1.0, "silver": 0.95, "gold": 0.90}
BOOK_PROMO_THRESHOLD = 100.0
BOOK_PROMO_REDUCTION = 10.0


def subtotal(items):
    """计算订单小计。items: [{price, qty, sku_type}]"""
    total = 0.0
    for it in items:
        total += it["price"] * it["qty"]
    return total


def book_promotion(items):
    """书籍类满 100 减 10，返回减免金额。"""
    book_total = sum(
        it["price"] * it["qty"] for it in items if it.get("sku_type") == "book"
    )
    # 修复 #1：需求为"满 100 元"（含 100），使用 >=（边界值缺陷）
    if book_total >= BOOK_PROMO_THRESHOLD:
        return BOOK_PROMO_REDUCTION
    return 0.0


def member_discount_rate(member_level):
    if member_level not in MEMBER_DISCOUNT:
        raise ValueError(f"unknown member level: {member_level}")
    return MEMBER_DISCOUNT[member_level]


def calculate_order_total(items, member_level="normal"):
    """计算订单应付总额 = (小计 - 品类满减) × 会员折扣，结果保留两位小数。

    [种子缺陷 #2] 忘记对结果做 round(..., 2)，
    浮点直乘会出现 100 * 0.95 = 95.00000000000001 之类的精度噪声。
    """
    if not items:
        return 0.0
    base = subtotal(items) - book_promotion(items)
    rate = member_discount_rate(member_level)
    # 修复 #2：按需求 ROUND_HALF_UP 保留两位小数（浮点精度缺陷）
    return float(Decimal(str(base * rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
