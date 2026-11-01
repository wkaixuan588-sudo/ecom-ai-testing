# -*- coding: utf-8 -*-
"""库存服务：扣减与回滚。

业务规则：
1. 扣减数量 qty 必须为正整数
2. 库存不足时应拒绝扣减并返回 False，不得出现负库存
3. 扣减成功返回 True 并更新库存
"""


def deduct(stock: dict, sku: str, qty) -> bool:
    """从 stock[sku] 扣减 qty 件。stock: {sku: 剩余数量}"""
    if sku not in stock:
        return False
    # 修复 #5：qty 必须为正整数（bool 不是合法数量），
    # 负数/0/浮点/bool 一律拒绝，防止反向刷库存
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        return False
    if qty > stock[sku]:
        return False
    stock[sku] -= qty
    return True
