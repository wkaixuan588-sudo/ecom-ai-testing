# AI-Native 测试平台：电商订单计价系统

[![CI](https://github.com/wkaixuan588-sudo/ecom-ai-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/wkaixuan588-sudo/ecom-ai-testing/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-80%20passed-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-98%25-success)

基于 DeepSeek Harness（DSH）多代理能力构建的 AI 测试工作流及其 Web 平台。
工作流覆盖 **用例生成 → 分层执行 → 多代理治理 → 修复回归 → 报告产出** 全链路，
平台将其产品化为可操作的四个功能区。

**一次完整运行的结果**：AI 生成 80 个测试用例，捕获 7 个缺陷（含边界值、精度、资损类），
全部修复后回归全绿，行覆盖率 98%。

- 📈 [在线 Allure 报告](https://wkaixuan588-sudo.github.io/ecom-ai-testing/)（中文界面，含红→绿趋势）
- 🔭 [Langfuse 公开运行数据](https://us.cloud.langfuse.com/project/cmvxgyyw300suad0lz6dker9g/traces/070084f03bc02772973cecafa9ff030a)（免登录，五阶段时间轴）
- 📸 [平台演示截图](reports/platform-demo.png)

---

## 核心特性

- **AI 用例生成，方法可追溯**——子代理按等价类划分、边界值分析、异常输入三种方法生成用例，每个用例标注所用方法，断言严格依据需求文档而非代码现状
- **多代理测试治理**——workflow 编排 7 个子代理：4 个并行覆盖率审计、2 个并行失败诊断、1 个风险评估汇总，输出遗漏场景清单与 P0–P3 修复优先级
- **多套件一键执行**——平台支持跨项目套件：本系统 80 用例回归、saucedemo PO 模式 UI 套件 20 用例
- **全链路可观测**——每轮运行上报 Langfuse trace（阶段时间轴 + 通过率/缺陷数评分），Allure 双运行趋势报告
- **引擎可插拔**——生成引擎支持 GLM / DeepSeek / 演示快照三模式切换，LLM 调用失败自动降级，演示不中断

## 工作流总览

```
需求/源码 ──► L1 单测生成 ─┐
                          ├─► 分层执行 ──► L4 多代理治理 ──► 修复回归 ──► 报告产出
接口契约 ──► L2 API 生成 ─┘        │              │
                              L3 UI 自动化    审计/诊断/定级
```

| 阶段 | 执行者 | 职责 | 结果 |
|---|---|---|---|
| L1 单元测试 | AI 子代理 | 按测试设计方法生成 46 用例 | 10 个失败用例锁定 5 个缺陷 |
| L2 API 测试 | AI 子代理（与 L1 并行） | 契约驱动生成 34 用例，覆盖状态码矩阵 | 12 个失败用例锁定接口层缺陷 |
| L3 UI 自动化 | playwright | 3 个端到端黄金链路场景 | 缺陷 #1 穿透三层复现 |
| L4 治理 | 7 个子代理 | 覆盖率审计 / 失败诊断 / 风险评估 | 37 个遗漏场景、7 组缺陷定级 |
| L5 修复回归 | 人工修复 + 全量回归 | 消除全部缺陷 | 80/80 通过，UI 复测一致 |

## 测试结果

```
修复前：80 用例 → 58 通过 / 22 失败
修复后：80 用例 → 80 通过 /   0 失败     行覆盖率 98%
缺陷：  7 发现 / 7 修复 / 7 回归验证
AI 参与：2 个用例生成子代理 + 7 个治理子代理
```

### 缺陷清单

| ID | 缺陷 | 层级 | 严重等级 | 发现方法 |
|---|---|---|---|---|
| BUG-01 | 满减边界写成 `>`，恰好 100 元不享受满减 | L1→L3 | Critical | 边界值分析 |
| BUG-02 | 金额未保留两位小数，浮点噪声透出 | L1 | Minor | 精度断言 |
| BUG-03 | 优惠券有效期开区间，到期当天被拒 | L1 | Minor | 时间边界 + monkeypatch |
| BUG-04 | 负数订单金额未校验，折扣券算出负优惠 | L1 | Critical | 非法输入 |
| BUG-05 | 库存 qty 无正整数校验，负数反向加库存 | L1 | Critical | 异常输入防御 |
| BUG-06 | API 非法参数返回 500/201 而非契约的 400 | L2 | Blocker | 接口契约测试 |
| BUG-07 | 前端金额展示未格式化 | L3 | Minor | UI 一致性检查 |

> BUG-01 被单元、API、UI 三个独立层级分别捕获，体现了分层测试的价值；
> BUG-02 在订单端点被 `round()` 掩盖，仅在券试算端点暴露——同类缺陷在不同出口的表现可能不一致。

## 平台功能

```bash
./scripts/start.sh          # 一键启动（自动加载 .env）
# 本机访问 http://127.0.0.1:8080/ ，局域网设备访问 http://<本机IP>:8080/
```

| 功能区 | 说明 |
|---|---|
| ① AI 生成功能用例 | 粘贴需求文档，按等价类/边界值/异常输入输出用例表格 |
| ② AI 生成接口用例 | 粘贴接口契约，输出含状态码与断言要点的用例矩阵 |
| ③ 一键执行 | 套件选择（全量回归 / UI 套件），实时日志，Allure 同步采集 |
| ④ 报告中心 | xlsx 报告下载 / Allure 在线报告 / Langfuse 看板 / 治理报告 |

生成引擎通过环境变量切换：`LLM_PROVIDER=mock | glm | deepseek`（mock 为真实用例快照，无需 API Key；LLM 异常时自动降级）。

## 快速开始

```bash
# 环境
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 全量回归（80 用例）
pytest tests/unit tests/api -v

# 启动被测系统
flask --app app.api run --port 8765

# 启动测试平台
./scripts/start.sh

# 生成测试报告
python scripts/make_report.py          # xlsx
allure generate reports/allure-results -o reports/allure-report --clean --lang zh
```

### 复现"缺陷现场"（红→绿演示）

```bash
sed -i '' 's/book_total >= /book_total > /' app/pricing.py   # 临时还原 BUG-01
pytest tests/unit tests/api --alluredir=reports/allure-results -q
sed -i '' 's/book_total > /book_total >= /' app/pricing.py   # 恢复修复
pytest tests/unit tests/api --alluredir=reports/allure-results -q
allure generate reports/allure-results -o reports/allure-report --clean --lang zh
```

## 项目结构

```
ecom-ai-testing/
├── app/                        # 被测系统（计价引擎 / 优惠券 / 库存 / Flask API）
├── static/                     # 被测系统前端下单页
├── tests/unit/ · tests/api/    # 80 个 AI 生成的测试用例
├── webapp/                     # AI 测试平台（FastAPI + 单页前端）
├── workflows/test_governance.js    # L4 多代理治理编排脚本
├── scripts/                    # 报告生成 / Langfuse 上报 / 启动脚本
├── docs/                       # Dify 方案效果示意图
└── reports/                    # xlsx 报告 / Allure / 演示截图 / 指标 JSON
```

## 可观测性

- **Allure**：按 layer（unit/api）分层的用例导航、失败分类、双运行趋势；每个用例的 docstring 说明所用测试设计方法
- **Langfuse**：每轮流水线上报一条 trace（五阶段 span 时间轴，L4 内嵌三个子阶段），trace 级评分含 pass_rate / defects_open / line_coverage；上报脚本为 `scripts/run_pipeline_demo.py`，未配置密钥时自动进入 dry-run

## 工程备注

- 被测系统的 7 个缺陷均为高频真实错误模式（边界比较、浮点精度、区间语义、非法输入防御、参数校验缺失），用于验证测试工作流的检出能力
- `webapp/` 目录不可命名为 `platform`——与 Python 标准库 `platform` 模块冲突，会导致 pytest 内部导入异常
- Langfuse 密钥存于 `.env`（已 gitignore）；账号按区域隔离，`LANGFUSE_HOST` 须与注册区域一致

## Roadmap

- [ ] AI 用例质量评审：引入 LLM-as-Judge 按覆盖度/可测性/冗余度对生成用例打分
- [ ] 用例审核入库：AI 生成 → 人工审核 → YAML 用例库 → 定向执行
- [ ] 下单失败路径的库存回滚防护回归用例（L4 审计发现的零覆盖盲区）
