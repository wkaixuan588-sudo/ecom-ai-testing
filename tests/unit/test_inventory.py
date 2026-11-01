# -*- coding: utf-8 -*-
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.inventory import deduct


def test_deduct_normal():
    """等价类（有效输入）：库存充足，扣减成功且库存更新"""
    stock = {"A": 10}
    assert deduct(stock, "A", 3) is True
    assert stock["A"] == 7


def test_deduct_exact_stock():
    """边界值：扣减数量恰好等于剩余库存（qty == stock），成功且归零"""
    stock = {"A": 5}
    assert deduct(stock, "A", 5) is True
    assert stock["A"] == 0


def test_deduct_more_than_stock_rejected():
    """边界值：qty = stock + 1，拒绝且库存不变（不得负库存）"""
    stock = {"A": 5}
    assert deduct(stock, "A", 6) is False
    assert stock["A"] == 5


def test_deduct_unknown_sku():
    """异常输入（非法键）：sku 不存在返回 False"""
    assert deduct({}, "X", 1) is False


def test_deduct_qty_one():
    """边界值：最小正整数 qty=1 可扣减"""
    stock = {"A": 1}
    assert deduct(stock, "A", 1) is True
    assert stock["A"] == 0


def test_deduct_qty_zero_rejected():
    """异常输入（0）：qty=0 非正整数，应拒绝且库存不变"""
    stock = {"A": 5}
    assert deduct(stock, "A", 0) is False
    assert stock["A"] == 5


def test_deduct_qty_negative_rejected():
    """异常输入（负数）：qty=-5 必须拒绝，且不得反向增加库存"""
    stock = {"A": 5}
    assert deduct(stock, "A", -5) is False
    assert stock["A"] == 5


def test_deduct_qty_float_rejected():
    """异常输入（非法类型）：qty 为浮点数 2.5 非正整数，应拒绝"""
    stock = {"A": 5}
    assert deduct(stock, "A", 2.5) is False
    assert stock["A"] == 5


def test_deduct_qty_string_rejected():
    """异常输入（非法类型）：qty 为字符串应拒绝（或抛 TypeError），不得改动库存"""
    stock = {"A": 5}
    try:
        result = deduct(stock, "A", "3")
    except TypeError:
        result = False
    assert result is False
    assert stock["A"] == 5


def test_deduct_qty_none_rejected():
    """异常输入（空）：qty 为 None 应拒绝（或抛 TypeError），不得改动库存"""
    stock = {"A": 5}
    try:
        result = deduct(stock, "A", None)
    except TypeError:
        result = False
    assert result is False
    assert stock["A"] == 5


def test_deduct_bool_rejected():
    """异常输入（非法类型）：bool 是 int 子类但不应视为合法数量"""
    stock = {"A": 5}
    assert deduct(stock, "A", True) is False
    assert stock["A"] == 5
