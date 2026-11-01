# -*- coding: utf-8 -*-
"""生成面试项目测试报告 ecom-ai-testing/reports/test-report.xlsx"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = Workbook()
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)
CENTER = Alignment(horizontal="center", vertical="center")

def style_header(ws, ncols, row=1):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, THIN

# ---------- Sheet1 测试总览 ----------
ws = wb.active
ws.title = "测试总览"
rows = [
    ("指标", "修复前", "修复后"),
    ("测试用例总数", 80, 80),
    ("通过 / 失败", "58 / 22", "80 / 0"),
    ("单元测试（L1·AI 生成）", 46, 46),
    ("API 测试（L2·AI 生成）", 34, 34),
    ("UI 场景（L3·playwright）", 3, 3),
    ("代码行覆盖率", "98%", "98%"),
    ("发现缺陷数", 7, 7),
    ("已修复并回归通过", 0, 7),
    ("Workflow 子代理数", 7, 7),
]
for r in rows:
    ws.append(r)
style_header(ws, 3)
ws.column_dimensions["A"].width = 30
for col in "BC":
    ws.column_dimensions[col].width = 16

# ---------- Sheet2 缺陷清单 ----------
ws2 = wb.create_sheet("缺陷清单")
headers = ("缺陷ID", "标题", "所在层", "源码位置", "严重等级", "发现方法", "发现途径", "状态")
defects = [
    ("BUG-01", "书籍满减边界失效：恰好100元不减免（> 应为 >=）", "L1 计价引擎", "app/pricing.py:32", "Critical", "边界值分析", "L1单测+L2 API+L3 UI 全链路复现", "已修复"),
    ("BUG-02", "金额未保留两位小数，浮点噪声透出（30.000000000000004）", "L1 计价引擎/优惠券", "app/pricing.py:53 / coupon.py:38", "Minor", "精度/等价类", "L2 API（券试算端点暴露）", "已修复"),
    ("BUG-03", "优惠券有效期开区间，到期当天整点被拒", "L1 优惠券", "app/coupon.py:29", "Minor", "时间边界值", "L1单测+L2 API（monkeypatch 控时）", "已修复"),
    ("BUG-04", "负数订单金额未校验，折扣券算出负优惠（反向加钱）", "L1 优惠券", "app/coupon.py:21", "Critical", "非法输入/安全", "L1单测+L2 API", "已修复"),
    ("BUG-05", "库存扣减 qty 无正整数校验，负数反向加库存（可无限刷）", "L1 库存", "app/inventory.py:15", "Critical", "异常输入防御", "L1单测+L2 API（5个用例锁定）", "已修复"),
    ("BUG-06", "API 参数校验缺失：非法 qty/member_level/order_amount 返回 500 或 201 而非 400", "L2 API", "app/api.py:56/64/86", "Blocker", "接口契约测试", "L2 API（12个失败用例归并）", "已修复"),
    ("BUG-07", "前端金额展示未格式化，浮点噪声可原样透出", "L3 前端", "static/index.html:74", "Minor", "UI 一致性检查", "L3 playwright 场景测试+多代理诊断", "已修复"),
]
ws2.append(headers)
for d in defects:
    ws2.append(d)
style_header(ws2, len(headers))
widths = (9, 46, 15, 30, 10, 15, 32, 9)
for i, w in enumerate(widths, 1):
    ws2.column_dimensions[chr(64 + i)].width = w
sev_fill = {"Critical": "FFC7CE", "Blocker": "FF9999", "Minor": "FFEB9C"}
for r in range(2, len(defects) + 2):
    sev = ws2.cell(row=r, column=5).value
    ws2.cell(row=r, column=5).fill = PatternFill("solid", fgColor=sev_fill.get(sev, "FFFFFF"))
    for c in range(1, len(headers) + 1):
        ws2.cell(row=r, column=c).border = THIN
        ws2.cell(row=r, column=c).alignment = Alignment(vertical="center", wrap_text=True)

# ---------- Sheet3 用例统计 ----------
ws3 = wb.create_sheet("用例统计")
ws3.append(("测试套件", "用例数", "修复前通过", "修复后通过", "设计方法"))
suites = [
    ("tests/unit/test_pricing.py", 19, "—", "19/19", "等价类+边界值+精度断言"),
    ("tests/unit/test_coupon.py", 16, "—", "16/16", "等价类+时间边界+非法输入"),
    ("tests/unit/test_inventory.py", 11, "—", "11/11", "异常输入防御（负数/0/浮点/bool）"),
    ("tests/api/test_orders_api.py", 34, "22/34", "34/34", "契约驱动+状态码矩阵+monkeypatch"),
    ("UI 场景（playwright-cli）", 3, "2/3", "3/3", "端到端黄金链路+组合场景"),
]
for s in suites:
    ws3.append(s)
style_header(ws3, 5)
for i, w in enumerate((34, 10, 12, 12, 36), 1):
    ws3.column_dimensions[chr(64 + i)].width = w

# ---------- Sheet4 风险评估与建议 ----------
ws4 = wb.create_sheet("风险评估与建议")
ws4.append(("类别", "内容"))
risks = [
    ("修复优先级", "P0：API 参数校验缺失（Blocker，服务可被击穿为 500）"),
    ("修复优先级", "P1：库存可反向刷取 / 负金额负优惠 / 满减边界失效（Critical，资损类）"),
    ("修复优先级", "P2：非法 member_level 500（需同时考虑扣库存后失败不回滚）"),
    ("修复优先级", "P3：有效期边界语义（Minor，随 P1 一并修复）"),
    ("测试资产缺口 Top1", "下单失败路径不回滚库存：零覆盖，需补「失败后断言库存不变」防回归用例"),
    ("测试资产缺口 Top2", "优惠券参数值域（rate>1/负 rate/满减额>订单额）：资金安全盲区"),
    ("测试资产缺口 Top3", "负价格/负数量可进入计价引擎：与 BUG-05 同源，pricing 层需补锁定用例"),
    ("流程结论", "7 个缺陷全部修复，80 用例回归全绿，形成「AI 用例生成→执行→多代理诊断→修复→回归」闭环"),
]
for r in risks:
    ws4.append(r)
style_header(ws4, 2)
ws4.column_dimensions["A"].width = 20
ws4.column_dimensions["B"].width = 90
for r in range(2, len(risks) + 2):
    ws4.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="center")

wb.save("reports/test-report.xlsx")
print("saved")
