# -*- coding: utf-8 -*-
"""订单 API 契约测试（Flask test_client + pytest）。

被测对象: app/api.py 暴露的三个接口
  GET  /api/products
  POST /api/orders                body: {sku, qty, member_level, coupon_id}
  POST /api/coupons/<cid>/apply   body: {order_amount}

契约（模块 docstring + 需求文档 v1.2）:
  - 非法参数 -> 400 + 明确 error
  - sku 不存在 -> 404
  - 库存不足 -> 409
  - 下单成功 -> 201
  - 所有金额计算结果保留两位小数
  - 书籍满 100 元（含 100）立减 10
  - 优惠券有效期闭区间 [valid_from, valid_to]
  - 订单金额必须为正数

注意: 本文件严格按契约断言。若用例失败，说明接口现状违反契约（缺陷），
失败是预期用来暴露缺陷的手段，不得为凑绿修改断言或 app/ 源码。
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from datetime import datetime

import pytest

from app import api as api_module
from app import coupon as coupon_mod


# ----------------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_stock():
    """每个测试前后重置 api.py 的模块级 STOCK，保证测试隔离。"""
    original = dict(api_module.STOCK)
    api_module.STOCK.update(
        {sku: p["stock"] for sku, p in api_module.PRODUCTS.items()}
    )
    yield
    api_module.STOCK.clear()
    api_module.STOCK.update(original)


@pytest.fixture
def app():
    api_module.app.config["TESTING"] = True
    return api_module.app


@pytest.fixture
def client(app):
    return app.test_client()


def _order(client, **overrides):
    body = {"sku": "BK-001", "qty": 1, "member_level": "normal"}
    body.update(overrides)
    keys = [k for k, v in overrides.items() if v is _MISSING]
    for k in keys:
        del body[k]
    return client.post("/api/orders", json=body)


class _Missing:
    pass


_MISSING = _Missing()


# ----------------------------------------------------------------------------
# GET /api/products
# ----------------------------------------------------------------------------
def test_get_products_list(client):
    """GET /api/products —— 返回 200 与全部商品（sku/name/price/sku_type/stock）。

    验证点: 状态码 200；products 为列表且包含全部 3 个 sku；字段齐全。
    """
    resp = client.get("/api/products")
    assert resp.status_code == 200
    data = resp.get_json()
    skus = {p["sku"] for p in data["products"]}
    assert skus == {"BK-001", "BK-002", "EL-001"}
    for p in data["products"]:
        assert {"name", "price", "sku_type", "stock"} <= set(p)


# ----------------------------------------------------------------------------
# POST /api/orders —— 正常路径与会员等级
# ----------------------------------------------------------------------------
def test_create_order_normal(client):
    """POST /api/orders normal —— 普通会员无折扣、无满减（89 < 100）。

    验证点: 201；payable == 89.0；coupon_saving == 0。
    """
    resp = _order(client, sku="BK-001", qty=1, member_level="normal")
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["payable"] == 89.0
    assert data["coupon_saving"] == 0.0


def test_create_order_silver(client):
    """POST /api/orders silver —— 95 折，金额保留两位小数。

    验证点: 201；payable == round(89 * 0.95, 2) == 84.55。
    """
    resp = _order(client, sku="BK-001", qty=1, member_level="silver")
    assert resp.status_code == 201
    assert resp.get_json()["payable"] == 84.55


def test_create_order_gold(client):
    """POST /api/orders gold —— 9 折（399 -> 359.1），无书籍满减（非 book）。

    验证点: 201；payable == 359.1。
    """
    resp = _order(client, sku="EL-001", qty=1, member_level="gold")
    assert resp.status_code == 201
    assert resp.get_json()["payable"] == 359.1


def test_create_order_default_member_level(client):
    """POST /api/orders 缺省 member_level —— 默认 normal，无折扣。

    验证点: 201；payable == 89.0（等价 normal）。
    """
    body = {"sku": "BK-001", "qty": 1}
    resp = client.post("/api/orders", json=body)
    assert resp.status_code == 201
    assert resp.get_json()["payable"] == 89.0


def test_create_order_book_promo_above_threshold(client):
    """POST /api/orders 书籍满减（高于阈值）—— 89*2=178 > 100 立减 10。

    验证点: 201；normal payable == 168.0。
    """
    resp = _order(client, sku="BK-001", qty=2, member_level="normal")
    assert resp.status_code == 201
    assert resp.get_json()["payable"] == 168.0


def test_create_order_book_promo_below_threshold(client):
    """POST /api/orders 书籍满减（低于阈值）—— 89 < 100 不减免。

    验证点: 201；payable == 89.0。
    """
    resp = _order(client, sku="BK-001", qty=1, member_level="normal")
    assert resp.status_code == 201
    assert resp.get_json()["payable"] == 89.0


def test_create_order_book_promo_exact_100(client):
    """POST /api/orders 书籍满减边界 —— BK-002 单价 100，qty=1 恰好 100 元。

    验证点（需求: 满 100 含 100）: 201 且 payable == 90.0。
    现状缺陷 #1: pricing.book_promotion 用严格大于，实际返回 100.0 -> 用例失败。
    """
    resp = _order(client, sku="BK-002", qty=1, member_level="normal")
    assert resp.status_code == 201
    assert resp.get_json()["payable"] == 90.0


def test_create_order_qty_equals_stock(client):
    """POST /api/orders 库存边界 —— qty == stock(10) 应成功并清空库存。

    验证点: 第一次 201；随后再下 1 件 -> 409。
    """
    resp = _order(client, sku="EL-001", qty=10, member_level="normal")
    assert resp.status_code == 201
    resp2 = _order(client, sku="EL-001", qty=1, member_level="normal")
    assert resp2.status_code == 409


def test_stock_deducted_after_order(client):
    """POST /api/orders 副作用 —— 下单成功后模块级 STOCK 被正确扣减。

    验证点: BK-001 下 3 件后 STOCK["BK-001"] == 47。
    """
    _order(client, sku="BK-001", qty=3)
    assert api_module.STOCK["BK-001"] == 47


def test_create_order_with_full_reduction_coupon(client):
    """POST /api/orders 带满减券 —— EL-001 399 >= 200 减 20。

    验证点: 201；coupon_saving == 20.0；payable == 379.0。
    """
    resp = _order(client, sku="EL-001", qty=1, member_level="normal",
                  coupon_id="C-FULL-20")
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["coupon_saving"] == 20.0
    assert data["payable"] == 379.0


def test_create_order_with_unknown_coupon(client):
    """POST /api/orders 带不存在券号的宽容行为（契约未定义 404）。

    验证点: 201 且 coupon_saving == 0（不崩溃、不倒扣）。
    """
    resp = _order(client, sku="BK-001", qty=1, member_level="normal",
                  coupon_id="C-NOPE")
    assert resp.status_code == 201
    assert resp.get_json()["coupon_saving"] == 0.0


# ----------------------------------------------------------------------------
# POST /api/orders —— 404 / 409 分支
# ----------------------------------------------------------------------------
def test_order_unknown_sku_404(client):
    """POST /api/orders sku 不存在 —— 契约要求 404 + error。

    验证点: 404；body 含非空 error 字段。
    """
    resp = _order(client, sku="NOPE-000", qty=1)
    assert resp.status_code == 404
    assert resp.get_json()["error"]


def test_order_missing_sku_404(client):
    """POST /api/orders 缺 sku 字段 —— sku 为 None 等价于不存在。

    验证点: 404 + error。
    """
    resp = client.post("/api/orders", json={"qty": 1, "member_level": "normal"})
    assert resp.status_code == 404
    assert resp.get_json()["error"]


def test_order_insufficient_stock_409(client):
    """POST /api/orders 库存不足 —— EL-001 仅 10 件，请求 11 件。

    验证点: 409；error 提及库存；STOCK 未被扣减。
    """
    resp = _order(client, sku="EL-001", qty=11)
    assert resp.status_code == 409
    assert resp.get_json()["error"]
    assert api_module.STOCK["EL-001"] == 10


# ----------------------------------------------------------------------------
# POST /api/orders —— 非法参数（契约: 400 + 明确 error）
# 现状缺陷 #6: api.py 未校验 qty，以下用例预期失败以暴露缺陷
# ----------------------------------------------------------------------------
def test_order_qty_zero_400(client):
    """POST /api/orders qty=0 —— 非法参数，契约要求 400。

    验证点: 400 + error。现状: 返回 201（缺陷 #6/#5）-> 用例失败。
    """
    resp = _order(client, qty=0)
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_order_qty_negative_400(client):
    """POST /api/orders qty=-1 —— 非法参数，契约要求 400，且不得增加库存。

    验证点: 400 + error；STOCK 不变。现状: 返回 201 且库存 +1（缺陷 #5）-> 失败。
    """
    resp = _order(client, qty=-1)
    assert resp.status_code == 400
    assert resp.get_json()["error"]
    assert api_module.STOCK["BK-001"] == 50


def test_order_qty_not_numeric_400(client):
    """POST /api/orders qty="abc" —— 非法参数，契约要求 400。

    验证点: 400 + error。现状: inventory.deduct 内 TypeError -> 500 -> 失败。
    """
    resp = _order(client, qty="abc")
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_order_qty_missing_400(client):
    """POST /api/orders 缺 qty 字段 —— 非法参数，契约要求 400。

    验证点: 400 + error。现状: None 与 int 比较抛 TypeError -> 500 -> 失败。
    """
    resp = _order(client, qty=_MISSING)
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_order_qty_float_400(client):
    """POST /api/orders qty=1.5 —— 数量必须为正整数，契约要求 400。

    验证点: 400 + error。现状: 返回 201 且库存被扣成小数 -> 失败。
    """
    resp = _order(client, qty=1.5)
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_order_invalid_member_level_400(client):
    """POST /api/orders member_level="platinum" —— 非法参数，契约要求 400。

    验证点: 400 + error。现状: pricing 抛 ValueError -> 500 -> 失败。
    """
    resp = _order(client, member_level="platinum")
    assert resp.status_code == 400
    assert resp.get_json()["error"]


# ----------------------------------------------------------------------------
# POST /api/coupons/<cid>/apply —— 金额边界
# ----------------------------------------------------------------------------
def test_apply_full_reduction_above_threshold(client):
    """POST /api/coupons/C-FULL-20/apply 金额 250 —— 满 200 减 20。

    验证点: 200；saving == 20.0。
    """
    resp = client.post("/api/coupons/C-FULL-20/apply", json={"order_amount": 250})
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 20.0


def test_apply_full_reduction_exact_threshold(client):
    """POST /api/coupons/C-FULL-20/apply 金额恰为 200 —— 阈值闭边界（>=）。

    验证点: 200；saving == 20.0。
    """
    resp = client.post("/api/coupons/C-FULL-20/apply", json={"order_amount": 200})
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 20.0


def test_apply_full_reduction_below_threshold(client):
    """POST /api/coupons/C-FULL-20/apply 金额 199.99 —— 未达阈值无优惠。

    验证点: 200；saving == 0.0。
    """
    resp = client.post("/api/coupons/C-FULL-20/apply", json={"order_amount": 199.99})
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 0.0


def test_apply_discount_under_cap(client):
    """POST /api/coupons/C-DISC-85/apply 金额 200 —— 85 折优惠 30 元（< 封顶 50）。

    验证点: 200；saving 精确等于 30.0（需求: 金额保留两位小数）。
    现状缺陷 #2: coupon_saving 未 round，返回 30.000000000000004 -> 失败。
    """
    resp = client.post("/api/coupons/C-DISC-85/apply", json={"order_amount": 200})
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 30.0


def test_apply_discount_capped(client):
    """POST /api/coupons/C-DISC-85/apply 金额 500 —— 优惠 75 触发封顶 50。

    验证点: 200；saving == 50.0。
    """
    resp = client.post("/api/coupons/C-DISC-85/apply", json={"order_amount": 500})
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 50.0


def test_apply_unknown_coupon_404(client):
    """POST /api/coupons/C-NOPE/apply —— 券号不存在返回 404。

    验证点: 404 + error。
    """
    resp = client.post("/api/coupons/C-NOPE/apply", json={"order_amount": 250})
    assert resp.status_code == 404
    assert resp.get_json()["error"]


def test_apply_order_amount_missing_400(client):
    """POST /api/coupons/<cid>/apply 缺 order_amount —— 非法参数，契约要求 400。

    验证点: 400 + error。现状: None 参与乘法 -> 500 -> 失败。
    """
    resp = client.post("/api/coupons/C-FULL-20/apply", json={})
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_apply_order_amount_zero_400(client):
    """POST /api/coupons/<cid>/apply order_amount=0 —— 需求要求金额为正数。

    验证点: 400 + error。现状: 返回 200 saving=0 -> 失败。
    """
    resp = client.post("/api/coupons/C-FULL-20/apply", json={"order_amount": 0})
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_apply_order_amount_negative_400(client):
    """POST /api/coupons/C-DISC-85/apply order_amount=-100 —— 负数为非法参数。

    验证点: 400 + error。现状缺陷 #4: 折扣券算出 saving=-15 且返回 200 -> 失败。
    """
    resp = client.post("/api/coupons/C-DISC-85/apply",
                       json={"order_amount": -100})
    assert resp.status_code == 400
    assert resp.get_json()["error"]


# ----------------------------------------------------------------------------
# POST /api/coupons/<cid>/apply —— 时间边界（monkeypatch coupon 模块的 datetime）
# ----------------------------------------------------------------------------
class _FakeDateTime(datetime):
    """替换 coupon_mod.datetime，使 apply_coupon 的 now 可控。"""
    _now = None

    @classmethod
    def now(cls, tz=None):
        return cls._now


def _apply_at(client, monkeypatch, now, cid="C-FULL-20", amount=250):
    monkeypatch.setattr(coupon_mod, "datetime", _FakeDateTime)
    _FakeDateTime._now = now
    return client.post(f"/api/coupons/{cid}/apply", json={"order_amount": amount})


def test_apply_at_valid_from_boundary(client, monkeypatch):
    """POST /api/coupons/<cid>/apply now == valid_from —— 闭区间起点可用。

    验证点: 200；saving == 20.0。
    """
    resp = _apply_at(client, monkeypatch,
                     now=datetime(2026, 1, 1, 0, 0, 0))
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 20.0


def test_apply_at_valid_to_boundary(client, monkeypatch):
    """POST /api/coupons/<cid>/apply now == valid_to 整点 —— 闭区间终点当天仍可用。

    验证点（需求 v1.2 第 3 条）: 200 且 saving == 20.0。
    现状缺陷 #3: coupon.py 用 now < valid_to，返回 0.0 -> 用例失败。
    """
    resp = _apply_at(client, monkeypatch,
                     now=datetime(2026, 12, 31, 23, 59, 59))
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 20.0


def test_apply_after_valid_to(client, monkeypatch):
    """POST /api/coupons/<cid>/apply now > valid_to —— 过期券无优惠。

    验证点: 200；saving == 0.0。
    """
    resp = _apply_at(client, monkeypatch,
                     now=datetime(2027, 1, 1, 0, 0, 0))
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 0.0


def test_apply_before_valid_from(client, monkeypatch):
    """POST /api/coupons/<cid>/apply now < valid_from —— 未生效无优惠。

    验证点: 200；saving == 0.0。
    """
    resp = _apply_at(client, monkeypatch,
                     now=datetime(2025, 12, 31, 23, 59, 59))
    assert resp.status_code == 200
    assert resp.get_json()["saving"] == 0.0
