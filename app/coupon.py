# -*- coding: utf-8 -*-
"""优惠券规则引擎。

业务规则（需求文档 v1.2）：
1. 满减券：订单金额 >= threshold 时减免 amount
2. 折扣券：订单金额 × rate，最多不超过 cap（封顶金额）
3. 优惠券在 [valid_from, valid_to] 区间内有效（闭区间，到期当天仍可使用）
4. 订单金额必须为正数；不满足条件的券返回优惠 0 元
"""
from datetime import datetime


def apply_coupon(order_amount, coupon, now=None):
    """计算优惠券优惠金额。coupon 字典：
    {type: "full_reduction"|"discount", threshold, amount, rate, cap,
     valid_from: datetime, valid_to: datetime}
    """
    if now is None:
        now = datetime.now()

    # 修复 #4：订单金额必须为正数（负金额可算出负优惠/反向加钱）
    if not isinstance(order_amount, (int, float)) or isinstance(order_amount, bool) \
            or order_amount <= 0:
        return 0.0

    if coupon is None:
        return 0.0

    # 修复 #3：有效期为闭区间 [valid_from, valid_to]，到期当天仍可用
    if not (coupon["valid_from"] <= now <= coupon["valid_to"]):
        return 0.0

    if coupon["type"] == "full_reduction":
        if order_amount >= coupon["threshold"]:
            return coupon["amount"]
        return 0.0

    if coupon["type"] == "discount":
        saving = order_amount * (1 - coupon["rate"])
        # 折扣券封顶；修复 #2：结果保留两位小数
        return round(min(saving, coupon.get("cap", float("inf"))), 2)

    return 0.0
