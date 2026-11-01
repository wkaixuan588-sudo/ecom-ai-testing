# AI-Native 软件测试实战项目：电商订单计价系统

> 基于 DeepSeek Harness（DSH）多代理能力搭建的「AI 用例生成 → 分层执行 → 多代理诊断 → 修复回归 → 报告产出」全流程测试工作流。
> 一次真实完整运行：**80 个测试用例、7 个缺陷全链路捕获并修复回归全绿、7 个子代理协同治理**。

---

## 1. 项目定位（面试一句话）

> 我没有只"写自动化脚本"，而是把 AI 作为测试流程的第一公民：**用例由 AI 按测试设计方法生成、执行结果由多代理分工诊断、缺陷按优先级闭环修复，全程人只做决策**。这就是我理解的 AI-native 测试。

## 2. 被测系统（SUT）

电商订单计价系统，三层架构，代码中预埋 7 个真实缺陷（均为业界高频错误模式）：

```
ecom-ai-testing/
├── app/
│   ├── pricing.py      # L1 计价引擎：会员折扣、书籍满100减10、金额精度
│   ├── coupon.py       # L1 优惠券：满减券/折扣券、有效期、金额校验
│   ├── inventory.py    # L1 库存：扣减校验（防负数刷库存）
│   └── api.py          # L2 Flask API：/api/orders、/api/coupons/<cid>/apply
├── static/index.html   # L3 前端下单页（金额展示逻辑）
├── tests/unit/         # 46 个单元测试（AI 子代理生成）
├── tests/api/          # 34 个 API 测试（AI 子代理生成）
├── workflows/test_governance.js   # L4 多代理测试治理编排脚本
└── reports/            # xlsx 报告 / UI 截图 / 指标 JSON
```

## 3. AI 工作流设计（方案六逐步落地，难度递增）

| 阶段 | 难度 | AI 环节 | 人的角色 | 实际产出 |
|---|---|---|---|---|
| **L1 单元测试** | ★ | 子代理 A 读源码+需求注释，按**等价类/边界值/异常输入**生成 46 用例（断言严格按需求而非现状） | 审核用例设计方法 | 36 过 / 10 失败 → 缺陷 #1–#5 |
| **L2 API 测试** | ★★ | 子代理 B 按**接口契约**（状态码矩阵、非法参数、monkeypatch 控时）生成 34 用例，与 L1 **并行执行** | 定义契约 | 22 过 / 12 失败 → 缺陷 #6 + 上层复现 |
| **L3 UI 测试** | ★★★ | 我直接驱动 playwright-cli 真实浏览器跑 3 个端到端场景 | 设计黄金链路 | 金卡购书应付 ¥90（预期 81），缺陷 #1 **穿透三层复现** |
| **L4 多代理治理** | ★★★★ | workflow 编排 7 个子代理：**覆盖率审计（4 并行）→ 失败诊断（2 并行）→ 风险评估（1 汇总）** | 决策修复顺序 | 30+ 遗漏场景、缺陷 P0–P3 定级、额外发现"下单失败不回滚库存"零覆盖盲区 |
| **L5 修复回归** | ★★★★★ | 修复 7 缺陷 → 全量回归 | 执行修复 | **80 用例全绿**，UI 复测 ¥81.00，xlsx 报告产出 |

## 4. 缺陷清单（全部由测试捕获并修复）

| ID | 缺陷 | 层 | 严重等级 | 发现方法 |
|---|---|---|---|---|
| BUG-01 | 满减边界 `>` vs `>=`，恰 100 元不减 | L1→L3 全链路 | Critical | 边界值分析 |
| BUG-02 | 金额未保留两位小数（30.000000000000004） | L1 | Minor | 精度断言 |
| BUG-03 | 优惠券有效期开区间，到期当天被拒 | L1 | Minor | 时间边界 + monkeypatch |
| BUG-04 | 负金额未校验，算出负优惠（反向加钱） | L1 | Critical | 非法输入 |
| BUG-05 | qty 无校验，负数反向加库存（可无限刷） | L1 | Critical | 异常输入防御 |
| BUG-06 | API 非法参数返回 500/201 而非 400 | L2 | Blocker | 接口契约测试 |
| BUG-07 | 前端金额未格式化 | L3 | Minor | UI 一致性 |

**亮点**：BUG-01 由三个独立层分别捕获（单测、API、UI），证明分层的价值；BUG-02 在 orders 端点被 `round()` 掩盖，仅在券试算端点暴露——讲解"缺陷掩盖"的好素材。

## 5. 关键数字

```
修复前：80 用例 → 58 过 / 22 失败，行覆盖率 98%
修复后：80 用例 → 80 过 /  0 失败，行覆盖率 98%
缺陷：7 发现 / 7 修复 / 7 回归验证
AI 参与：2 个用例生成子代理 + 7 个治理子代理 = 9 个代理协同
```

## 6. 如何复现

```bash
cd ecom-ai-testing
.venv/bin/python -m pytest tests/unit tests/api -v     # 全量回归（全绿）
.venv/bin/python -m flask --app app.api run --port 8765 # 起被测服务
# UI：浏览器打开 http://127.0.0.1:8765/ 金卡+持续交付×1 → 应付 ¥81.00
# 报告：reports/test-report.xlsx；工作流脚本：workflows/test_governance.js
```

> 想看"缺陷现场"：`git log` 找到修复 commit 之前的版本即可重放红→绿全过程。

### 6.1 测试结果可视化（Allure 已接入）

```bash
cd ecom-ai-testing
# 双运行生成带红→绿趋势的报告（缺陷现场 + 修复后）
sed -i '' 's/book_total >= /book_total > /' app/pricing.py   # 还原 BUG-01 现场
.venv/bin/python -m pytest tests/unit tests/api --alluredir=reports/allure-results -q
sed -i '' 's/book_total > /book_total >= /' app/pricing.py   # 恢复修复
.venv/bin/python -m pytest tests/unit tests/api --alluredir=reports/allure-results -q
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report     # 浏览器查看总览/趋势/分类/Suites
```

报告内容：按 layer（unit/api）分层的用例导航、失败分类、双运行趋势（3 failed → 0 failed）、
每个用例的 docstring 设计方法说明。截图证据：`reports/allure-dashboard.png`。

### 6.2 AI 工作流运行数据看板（Langfuse）

`scripts/run_pipeline_demo.py` 把每轮流水线运行上报为一条 Langfuse trace：
五阶段 span 时间轴（L1/L2 并行、L4 内嵌三 phase）+ trace 级 score（pass_rate / defects_open / 覆盖率），
在 Langfuse 看板形成跨轮趋势与单轮下钻视图——即"AI 测试流水线的监控大盘"。

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...   # cloud.langfuse.com 免费注册获取（注意选择 US 区域）
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https://us.cloud.langfuse.com   # 区域须与注册时一致（账号按区域隔离）
.venv/bin/python scripts/run_pipeline_demo.py --backfill  # 回填 Round1/2 历史
.venv/bin/python scripts/run_pipeline_demo.py             # Round3 现场实时上报
# 不配置密钥即为 dry-run 演练模式（打印 JSON，不联网）
```

密钥存放在 `.env`（已加入 `.gitignore`）。每次上报会打印 trace 的看板直达链接，
在 Langfuse UI 中可看到跨轮趋势（Round1 0.725 → Round3 1.0）与单轮五阶段下钻。

### 6.3 AI 测试平台（路线 C · 本机版）

```bash
cd ecom-ai-testing
.venv/bin/python -m uvicorn webapp.main:app --host 0.0.0.0 --port 8080
# 本机访问 http://127.0.0.1:8080/ ；同一局域网设备访问 http://<本机IP>:8080/
```

平台四区：①AI 生成功能用例（等价类/边界值/异常输入）②AI 生成接口用例（契约驱动）
③一键执行（pytest 80 用例实时日志 + Allure 采集）④报告中心（xlsx / Allure / Langfuse 公开看板 / L4 治理报告）。

- 生成引擎三模式：`LLM_PROVIDER=mock|glm|deepseek`（mock 为项目真实用例快照，不依赖 Key）
- 演示截图：`reports/platform-demo.png`
- 工程教训：后端目录不可命名 `platform`（与 Python 标准库冲突，本项目真实踩坑并记录）
- GitHub Pages：`gh-pages` 分支含 Allure 在线报告，推送后 Settings → Pages → 选 gh-pages 分支即生效

## 7. 面试讲解要点

1. **测试设计方法不是空话**：每个 AI 生成用例的 docstring 都标注了等价类/边界值/异常输入，可现场翻代码。
2. **AI 生成 ≠ 点缀**：80 个用例中 80 个由子代理生成，我负责审核方法与契约定义。
3. **多代理编排**：workflows/test_governance.js 是可复用资产，换一个被测系统改路径即可复跑。
4. **闭环思维**：不止发现缺陷——诊断定级 → 修复 → 回归全绿 → 报告，这是测试左移+右移的完整链路。
5. **诚实边界**：AI 也会漏（如"下单失败不回滚库存"是治理阶段才发现的盲区），所以人的评审与风险判断仍不可替代——这一点面试官通常很认可。
