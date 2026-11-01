#!/bin/bash
# AI 测试平台一键启动
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && source .env && set +a
echo "启动 AI-Native 测试平台..."
echo "  本机入口:   http://127.0.0.1:8080/"
IP=$(ipconfig getifaddr en0 2>/dev/null)
[ -n "$IP" ] && echo "  局域网入口: http://$IP:8080/  （同一 Wi-Fi 的面试官可访问）"
.venv/bin/python -m uvicorn webapp.main:app --host 0.0.0.0 --port 8080
