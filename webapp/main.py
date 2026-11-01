# -*- coding: utf-8 -*-
"""AI 测试平台后端（FastAPI）——四件套：功能用例生成 / 接口用例生成 / 一键执行 / 测试报告。

启动：.venv/bin/python -m uvicorn webapp.main:app --host 0.0.0.0 --port 8080
注意：目录名不可叫 platform（与 Python 标准库冲突，真实踩坑一次）。
"""
import json
import subprocess
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .llm_client import generate

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="AI-Native 测试平台", version="1.0.0-mvp")

# ---------- 静态资源 ----------
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")
ALLURE_DIR = ROOT / "reports" / "allure-report"
if ALLURE_DIR.exists():
    app.mount("/allure", StaticFiles(directory=ALLURE_DIR, html=True), name="allure")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


# ---------- ① ② 用例生成 ----------
@app.post("/api/gen/functional")
def gen_functional(body: dict):
    return generate("functional", body.get("requirement", ""))


@app.post("/api/gen/api")
def gen_api(body: dict):
    return generate("api", body.get("contract", ""))


# ---------- ③ 一键执行（后台任务 + 轮询） ----------
_TASKS: dict[str, dict] = {}


def _run_pytest(tid: str):
    log_path = ROOT / "reports" / f"run-{tid}.log"
    with open(log_path, "w") as f:
        proc = subprocess.run(
            [str(ROOT / ".venv/bin/python"), "-m", "pytest",
             "tests/unit", "tests/api", "-v", "--tb=line", "--alluredir=reports/allure-results"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600,
        )
        f.write(proc.stdout)
    _TASKS[tid]["done"] = True


@app.post("/api/run")
def start_run():
    tid = uuid.uuid4().hex[:8]
    _TASKS[tid] = {"done": False}
    threading.Thread(target=_run_pytest, args=(tid,), daemon=True).start()
    return {"task_id": tid}


@app.get("/api/run/{tid}")
def run_status(tid: str):
    task = _TASKS.get(tid)
    log_path = ROOT / "reports" / f"run-{tid}.log"
    if task is None:
        return JSONResponse({"error": "unknown task"}, status_code=404)
    log = log_path.read_text(encoding="utf-8") if log_path.exists() else "启动中…\n"
    return {"done": task["done"], "log": "\n".join(log.splitlines()[-200:])}


# ---------- ④ 报告 ----------
@app.get("/api/report/xlsx")
def report_xlsx():
    p = ROOT / "reports" / "test-report.xlsx"
    if not p.exists():
        return JSONResponse({"error": "report not generated"}, status_code=404)
    return FileResponse(p, filename="AI测试报告.xlsx", media_type="application/vnd.ms-excel")


@app.get("/api/governance")
def governance():
    """L4 多代理治理结果导入展示（4a 方案）。"""
    p = ROOT / "reports" / "workflow-result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"workflow": "test-governance", "phases": []}


@app.get("/api/langfuse")
def langfuse_links():
    p = Path(__file__).parent / "langfuse_links.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"traces": []}
