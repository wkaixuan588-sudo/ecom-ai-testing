# -*- coding: utf-8 -*-
"""订单 API（Flask）。

接口契约：
GET  /api/products              商品列表
POST /api/orders                创建订单，body: {sku, qty, member_level, coupon_id}
POST /api/coupons/<cid>/apply   试算优惠券优惠金额，body: {order_amount}
"""
from datetime import datetime, timedelta

from flask import Flask, jsonify, request

from . import coupon as coupon_mod
from . import inventory, pricing

app = Flask(__name__, static_folder="../static", static_url_path="/static")

# ---- 内存数据 ----
PRODUCTS = {
    "BK-001": {"name": "软件测试的艺术", "price": 89.0, "sku_type": "book", "stock": 50},
    "BK-002": {"name": "持续交付", "price": 100.0, "sku_type": "book", "stock": 30},
    "EL-001": {"name": "机械键盘", "price": 399.0, "sku_type": "electronics", "stock": 10},
}
STOCK = {sku: p["stock"] for sku, p in PRODUCTS.items()}

COUPONS = {
    "C-FULL-20": {
        "type": "full_reduction", "threshold": 200.0, "amount": 20.0,
        "valid_from": datetime(2026, 1, 1), "valid_to": datetime(2026, 12, 31, 23, 59, 59),
    },
    "C-DISC-85": {
        "type": "discount", "rate": 0.85, "cap": 50.0,
        "valid_from": datetime(2026, 1, 1), "valid_to": datetime(2026, 12, 31, 23, 59, 59),
    },
}


@app.get("/api/products")
def get_products():
    return jsonify({"products": [
        {"sku": sku, **info} for sku, info in PRODUCTS.items()
    ]})


@app.post("/api/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    sku = data.get("sku")
    qty = data.get("qty")
    member_level = data.get("member_level", "normal")
    coupon_id = data.get("coupon_id")

    if sku not in PRODUCTS:
        return jsonify({"error": "sku not found"}), 404

    # 修复 #6：参数契约校验前置 —— 非法参数一律 400 + 明确 error
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        return jsonify({"error": "qty must be a positive integer"}), 400
    if member_level not in pricing.MEMBER_DISCOUNT:
        return jsonify({"error": "invalid member_level"}), 400

    # [种子缺陷 #6] qty 非法（0 / 负数 / 非数字）时未做参数校验，
    # 会带着脏数据穿透到计价与库存层，最终以 500 内部错误返回，
    # 而契约要求返回 400 + 明确的 error message —— 契约/健壮性缺陷
    if not inventory.deduct(STOCK, sku, qty):
        return jsonify({"error": "insufficient stock"}), 409

    item = {"price": PRODUCTS[sku]["price"], "qty": qty,
            "sku_type": PRODUCTS[sku]["sku_type"]}
    total = pricing.calculate_order_total([item], member_level)

    saving = 0.0
    if coupon_id:
        c = COUPONS.get(coupon_id)
        saving = coupon_mod.apply_coupon(total, c)

    return jsonify({
        "sku": sku, "qty": qty, "member_level": member_level,
        "coupon_id": coupon_id, "coupon_saving": saving,
        "payable": round(max(total - saving, 0.0), 2),
    }), 201


@app.post("/api/coupons/<cid>/apply")
def apply_coupon_api(cid):
    data = request.get_json(silent=True) or {}
    order_amount = data.get("order_amount")
    c = COUPONS.get(cid)
    if c is None:
        return jsonify({"error": "coupon not found"}), 404
    # 修复 #6 同源：order_amount 必须为正数，非法值返回 400
    if not isinstance(order_amount, (int, float)) or isinstance(order_amount, bool) \
            or order_amount <= 0:
        return jsonify({"error": "invalid order_amount"}), 400
    return jsonify({"coupon_id": cid, "saving": coupon_mod.apply_coupon(order_amount, c)})


@app.get("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765)
