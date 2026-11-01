# -*- coding: utf-8 -*-
"""LLM 调用层：GLM / DeepSeek（OpenAI 兼容）/ mock 演示模式 三模式切换。

环境变量（.env 或系统导出）：
  LLM_PROVIDER = mock | glm | deepseek
  LLM_BASE_URL = https://open.bigmodel.cn/api/paas/v4   （glm）
  LLM_MODEL    = glm-4.6
  LLM_API_KEY  = 你的 Key
未配置或 provider=mock 时返回项目真实运行过的用例快照（演示模式）。
"""
import json
import os

# ---------- 提示词模板（迁移自 L1/L2 子代理任务书） ----------
FUNCTIONAL_PROMPT = """你是资深测试工程师。根据以下需求文档，用【等价类划分 + 边界值分析 + 异常输入】
三种方法设计功能测试用例。只输出 JSON 数组，每个元素格式：
{{"title": "用例标题", "method": "等价类|边界值|异常输入", "precondition": "前置条件",
  "steps": "操作步骤", "expected": "预期结果"}}
要求覆盖：有效等价类、无效等价类（负数/0/非法类型）、每个边界的两侧（如阈值 N-0.01/N/N+0.01）。
至少 12 条。需求文档如下：

{content}"""

API_PROMPT = """你是资深接口测试工程师。根据以下接口契约，设计 API 测试用例。
只输出 JSON 数组，每个元素格式：
{{"name": "用例名", "method": "等价类|边界值|契约|异常输入", "http": "POST /api/xxx",
  "body": "请求体JSON（可为空）", "expected_status": 200, "checkpoint": "断言要点"}}
要求覆盖：正常路径、每个状态码分支（400/404/409 等）、非法参数（0/负数/字符串/缺字段）、
时间与金额边界。至少 12 条。接口契约如下：

{content}"""

# ---------- 演示模式快照（项目真实生成结果的节选） ----------
MOCK_FUNCTIONAL = [
    {"title": "书籍小计恰好100元应享受满100减10", "method": "边界值", "precondition": "购物车含书籍类商品", "steps": "添加持续交付(¥100)×1进入订单", "expected": "书籍满减10元生效，小计显示90"},
    {"title": "书籍小计99.99元不触发满减", "method": "边界值", "precondition": "购物车含书籍类商品", "steps": "添加书籍商品至小计99.99", "expected": "无满减，小计99.99"},
    {"title": "书籍小计100.01元触发满减", "method": "边界值", "precondition": "同上", "steps": "添加书籍商品至小计100.01", "expected": "满减10元生效"},
    {"title": "金卡会员9折计算", "method": "等价类", "precondition": "会员等级gold", "steps": "提交小计100的订单", "expected": "应付=100×0.9=90.00"},
    {"title": "银卡会员95折计算", "method": "等价类", "precondition": "会员等级silver", "steps": "提交小计100的订单", "expected": "应付95.00"},
    {"title": "未知会员等级被拒绝", "method": "异常输入", "precondition": "—", "steps": "以member_level=platinum下单", "expected": "返回400错误而非500"},
    {"title": "优惠券到期当天23:59:59仍可用", "method": "边界值(时间)", "precondition": "持有效期内满减券", "steps": "在valid_to当天使用", "expected": "闭区间语义，优惠生效"},
    {"title": "负数订单金额使用折扣券", "method": "异常输入", "precondition": "构造-100订单金额", "steps": "调用券试算", "expected": "返回0优惠，不得出现负优惠"},
    {"title": "金额计算保留两位小数", "method": "精度断言", "precondition": "小计267银卡会员", "steps": "计算应付", "expected": "244.15而非244.14999999999998"},
    {"title": "库存扣减数量为负数", "method": "异常输入", "precondition": "库存5件", "steps": "以qty=-5扣减", "expected": "拒绝且库存不变（防刷库存）"},
    {"title": "库存恰好等于购买量", "method": "边界值", "precondition": "库存3件", "steps": "购买3件", "expected": "扣减成功，库存归0"},
    {"title": "空订单计算总额", "method": "异常输入", "precondition": "—", "steps": "提交空items", "expected": "返回0而非报错"},
]

MOCK_API = [
    {"name": "正常下单返回201", "method": "契约", "http": "POST /api/orders", "body": '{"sku":"BK-001","qty":1,"member_level":"normal"}', "expected_status": 201, "checkpoint": "payable=89.0"},
    {"name": "qty=0 返回400", "method": "契约", "http": "POST /api/orders", "body": '{"sku":"BK-001","qty":0}', "expected_status": 400, "checkpoint": "error信息明确"},
    {"name": "qty=-1 返回400且库存不变", "method": "异常输入", "http": "POST /api/orders", "body": '{"sku":"BK-001","qty":-1}', "expected_status": 400, "checkpoint": "STOCK不被修改"},
    {"name": "qty为字符串返回400", "method": "异常输入", "http": "POST /api/orders", "body": '{"sku":"BK-001","qty":"abc"}', "expected_status": 400, "checkpoint": "非500"},
    {"name": "sku不存在返回404", "method": "契约", "http": "POST /api/orders", "body": '{"sku":"NOPE","qty":1}', "expected_status": 404, "checkpoint": "error=sku not found"},
    {"name": "库存不足返回409", "method": "契约", "http": "POST /api/orders", "body": '{"sku":"EL-001","qty":99}', "expected_status": 409, "checkpoint": "error=insufficient stock"},
    {"name": "满200减20券恰好达标", "method": "边界值", "http": "POST /api/coupons/C-FULL-20/apply", "body": '{"order_amount":200}', "expected_status": 200, "checkpoint": "saving=20"},
    {"name": "订单金额199.99不达标", "method": "边界值", "http": "POST /api/coupons/C-FULL-20/apply", "body": '{"order_amount":199.99}', "expected_status": 200, "checkpoint": "saving=0"},
    {"name": "order_amount缺失返回400", "method": "契约", "http": "POST /api/coupons/C-FULL-20/apply", "body": '{}', "expected_status": 400, "checkpoint": "非500"},
    {"name": "未知券ID返回404", "method": "契约", "http": "POST /api/coupons/NOPE/apply", "body": '{"order_amount":100}', "expected_status": 404, "checkpoint": "error=coupon not found"},
    {"name": "非法member_level返回400", "method": "异常输入", "http": "POST /api/orders", "body": '{"sku":"BK-001","qty":1,"member_level":"platinum"}', "expected_status": 400, "checkpoint": "非500"},
    {"name": "商品列表返回200且含3个SKU", "method": "契约", "http": "GET /api/products", "body": "", "expected_status": 200, "checkpoint": "products长度=3"},
]


def provider() -> str:
    return os.environ.get("LLM_PROVIDER", "mock")


def _live_generate(prompt: str) -> list:
    """OpenAI 兼容接口调用（GLM/DeepSeek 均适用）。"""
    import requests
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    key = os.environ["LLM_API_KEY"]
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": os.environ.get("LLM_MODEL", "glm-4.6"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        },
        timeout=120,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    # 兼容 markdown 代码块包裹的 JSON
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def generate(kind: str, content: str) -> dict:
    """kind: functional | api"""
    tpl = FUNCTIONAL_PROMPT if kind == "functional" else API_PROMPT
    if provider() in ("glm", "deepseek") and os.environ.get("LLM_API_KEY"):
        try:
            cases = _live_generate(tpl.format(content=content))
            mode = f"live({provider()})"
        except Exception as e:  # 失败降级到演示快照，保证演示不中断
            cases = MOCK_FUNCTIONAL if kind == "functional" else MOCK_API
            mode = f"mock(LLM调用失败降级: {type(e).__name__})"
    else:
        cases = MOCK_FUNCTIONAL if kind == "functional" else MOCK_API
        mode = "mock(演示快照)"
    return {"mode": mode, "count": len(cases), "cases": cases}
