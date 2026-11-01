/**
 * AI 测试治理 Workflow —— 方案六核心编排（三阶段多代理）
 *
 * Phase 1 覆盖率审计：并行子代理逐模块比对"源码分支 vs 现有测试"，
 *           找出测试遗漏场景（不运行测试，纯静态分析）
 * Phase 2 失败诊断：子代理实际运行 pytest，对失败用例归因到源码行，
 *           给出严重等级与修复建议
 * Phase 3 风险评估：汇总前两阶段结果，输出缺陷修复优先级矩阵
 *
 * 运行方式：由 DSH workflow 工具执行；产物写入 reports/workflow-result.json
 */
const ROOT = "ecom-ai-testing";
const PY = `${ROOT}/.venv/bin/python`;

const auditSchema = {
  type: "object",
  properties: {
    module: { type: "string" },
    branches_total: { type: "number" },
    branches_covered: { type: "number" },
    missing_scenarios: {
      type: "array",
      items: {
        type: "object",
        properties: {
          scenario: { type: "string" },
          branch: { type: "string" },
          risk: { type: "string", enum: ["high", "medium", "low"] },
          suggested_test: { type: "string" },
        },
        required: ["scenario", "branch", "risk", "suggested_test"],
      },
    },
  },
  required: ["module", "branches_total", "branches_covered", "missing_scenarios"],
};

const diagSchema = {
  type: "object",
  properties: {
    total_run: { type: "number" },
    passed: { type: "number" },
    failed: { type: "number" },
    defects: {
      type: "array",
      items: {
        type: "object",
        properties: {
          test_id: { type: "string" },
          source_location: { type: "string" },
          root_cause: { type: "string" },
          severity: { type: "string", enum: ["blocker", "critical", "major", "minor"] },
          fix_suggestion: { type: "string" },
        },
        required: ["test_id", "source_location", "root_cause", "severity", "fix_suggestion"],
      },
    },
  },
  required: ["total_run", "passed", "failed", "defects"],
};

// ---------- Phase 1: 覆盖率审计（4 模块并行，无栅栏依赖） ----------
phase("覆盖率审计");
const modules = ["pricing", "coupon", "inventory", "api"];
const audits = await parallel(
  modules.map((m) => () =>
    agent(
      `你是测试覆盖审计员。工作目录为仓库根目录。读取 ${ROOT}/app/${m}.py 源码与需求注释，` +
      `再读取 ${ROOT}/tests/unit/ 与 ${ROOT}/tests/api/ 下所有测试文件，` +
      `比对源码分支与测试场景：列出未覆盖/遗漏的场景（边界值、异常输入、组合条件），` +
      `评估风险等级并给出建议的测试用例描述。只分析，不修改任何文件。`,
      { label: `audit-${m}`, phase: "覆盖率审计", schema: auditSchema }
    )
  )
);

// ---------- Phase 2: 失败诊断（实际运行测试并归因） ----------
phase("失败诊断");
const diag = await parallel([
  () =>
    agent(
      `你是缺陷诊断工程师。工作目录为仓库根目录。执行 ` +
      `cd ${ROOT} && ${PY} -m pytest tests/unit tests/api -q --tb=short，` +
      `对每个失败用例：定位根因源码位置（文件:行号）、归纳缺陷根因（一句话）、` +
      `按 blocker/critical/major/minor 定级、给出修复建议。不修改任何文件。`,
      { label: "diagnose-suite", phase: "失败诊断", schema: diagSchema }
    ),
  () =>
    agent(
      `你是 UI 缺陷诊断工程师。工作目录为仓库根目录。读取 ${ROOT}/static/index.html 与 ` +
      `${ROOT}/app/api.py，分析前端下单页与后端 API 的金额一致性风险：` +
      `已知场景"金卡会员购买持续交付(¥100)×1 应付显示 ¥90（业务预期 81）"。` +
      `诊断该缺陷根因链路（前端→API→计价引擎），并检查 index.html 中金额展示逻辑的隐患。` +
      `total_run/passed/failed 填 1/0/1，把结论作为 defects[0]。不修改任何文件。`,
      { label: "diagnose-ui", phase: "失败诊断", schema: diagSchema }
    ),
]);

// ---------- Phase 3: 风险评估（依赖前两阶段，串行汇总） ----------
phase("风险评估");
const risk = await agent(
  `你是测试风险评估师。以下是多代理测试结果 JSON，请输出：` +
  `1) 缺陷修复优先级排序（结合严重等级与影响面）` +
  `2) 测试资产缺口 Top3（遗漏场景中风险最高者）` +
  `3) 一段面向测试负责人的总结（200字内）。` +
  `审计结果: ${JSON.stringify(audits)} 诊断结果: ${JSON.stringify(diag)}`,
  { label: "risk-assess", phase: "风险评估" }
);

return {
  phase1_coverage_audit: audits.filter(Boolean),
  phase2_defect_diagnosis: diag.filter(Boolean),
  phase3_risk_assessment: risk,
};
