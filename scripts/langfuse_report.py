# -*- coding: utf-8 -*-
"""Langfuse 上报层（SDK v5）：把 AI 测试流水线的每次运行变成一条可观测 trace。

环境变量（云版免费档，https://cloud.langfuse.com 注册后获取）：
  LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST

未配置密钥时自动进入 dry-run：只打印将要上报的 JSON，不联网。
"""
import json
import os
import time


def has_credentials() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))


def _now_ms() -> int:
    return int(time.time() * 1000)


def report_run(label: str, spans: list, scores: list, metadata: dict | None = None) -> bool:
    """spans: [{name, duration_ms, input, output, metadata, children?}]（duration 为示意时长）
    scores: [{name, value, comment}]"""
    payload = {"trace": f"AI测试流水线 · {label}", "spans": spans, "scores": scores,
               "metadata": metadata or {}}
    if not has_credentials():
        print("[dry-run] 未配置 Langfuse 密钥，以下为将要上报的数据：")
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str)[:2000])
        return False

    from langfuse import Langfuse
    from langfuse.types import TraceContext

    lf = Langfuse()
    trace_id = lf.create_trace_id()
    t0 = _now_ms()

    def add_children(parent, children, base_ms):
        for c in children:
            sp = parent.start_observation(
                name=c["name"], as_type="span",
                input=c.get("input"), output=c.get("output"), metadata=c.get("metadata"),
            )
            sp.end(end_time=base_ms + c.get("duration_ms", 1000))
            if c.get("children"):
                add_children(sp, c["children"], base_ms)

    # 根 span 即 trace 入口（五阶段挂在它下面）
    root = lf.start_observation(
        name=payload["trace"], as_type="chain",
        trace_context=TraceContext(trace_id=trace_id),
        metadata=payload["metadata"],
    )
    cursor = t0
    for s in spans:
        sp = root.start_observation(
            name=s["name"], as_type="span",
            input=s.get("input"), output=s.get("output"), metadata=s.get("metadata"),
        )
        dur = s.get("duration_ms", 1000)
        sp.end(end_time=cursor + dur)
        add_children(sp, s.get("children", []), cursor)
        cursor += dur
    root.end(end_time=cursor)

    for sc in scores:
        lf.create_score(name=sc["name"], value=sc["value"],
                        trace_id=trace_id, comment=sc.get("comment", ""))

    lf.flush()
    url = lf.get_trace_url(trace_id=trace_id)
    lf.shutdown()
    print(f"[langfuse] 已上报: {payload['trace']}（{len(spans)} spans, {len(scores)} scores）\n"
          f"[langfuse] 看板直达: {url}")
    return True


if __name__ == "__main__":
    # 自检：示例 trace
    report_run(
        "自检",
        spans=[{"name": "demo-span", "duration_ms": 100,
                "input": {"k": 1}, "output": {"ok": True}}],
        scores=[{"name": "pass_rate", "value": 1.0, "comment": "自检"}],
    )
