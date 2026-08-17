#!/bin/bash
# ============================================================
# 国内服务器部署/重启脚本
# 用法: 在服务器项目根目录执行 bash deploy.sh
# ============================================================

set -e

# ---------- 配置区（按实际情况修改） ----------
PORT=8000
HOST="0.0.0.0"
GIT_BRANCH="master"
# --------------------------------------------

# 自动定位项目目录（脚本所在目录）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  AI 智能客服助手 - 部署脚本"
echo "  项目目录: $PROJECT_DIR"
echo "  监听地址: $HOST:$PORT"
echo "=========================================="
echo ""

# ---------- 1. 拉取最新代码 ----------
echo "[1/5] 拉取最新代码..."
git fetch origin
git reset --hard "origin/$GIT_BRANCH"
echo "  -> 当前版本: $(git log --oneline -1)"
echo ""

# ---------- 2. 安装依赖 ----------
echo "[2/5] 安装 Python 依赖..."
# 检测虚拟环境
if [ -d "venv" ]; then
    echo "  -> 检测到 venv 虚拟环境，已激活"
    source venv/bin/activate
    pip install -r requirements.txt -q
elif [ -d ".venv" ]; then
    echo "  -> 检测到 .venv 虚拟环境，已激活"
    source .venv/bin/activate
    pip install -r requirements.txt -q
else
    pip install -r requirements.txt -q
fi
echo "  -> 依赖安装完成"
echo ""

# ---------- 3. 检查 .env 配置 ----------
echo "[3/5] 检查环境变量..."
if [ ! -f ".env" ]; then
    echo "  -> 警告: 未找到 .env 文件，将以模拟模式运行（无需 API Key）"
else
    echo "  -> .env 文件已存在"
fi
echo ""

# ---------- 4. 停止旧服务 ----------
echo "[4/5] 停止旧服务..."
# 方式1: 通过端口杀进程
if command -v fuser &> /dev/null; then
    fuser -k ${PORT}/tcp 2>/dev/null && echo "  -> 已通过端口 $PORT 停止旧进程" || echo "  -> 端口 $PORT 无占用"
elif command -v lsof &> /dev/null; then
    OLD_PID=$(lsof -t -i:${PORT} 2>/dev/null || true)
    if [ -n "$OLD_PID" ]; then
        kill $OLD_PID 2>/dev/null || true
        echo "  -> 已停止旧进程 (PID: $OLD_PID)"
    else
        echo "  -> 端口 $PORT 无占用"
    fi
else
    # 方式2: 通过进程名杀
    pkill -f "uvicorn app.main:app" 2>/dev/null && echo "  -> 已通过进程名停止旧进程" || echo "  -> 未找到运行中的 uvicorn 进程"
fi
sleep 1
echo ""

# ---------- 5. 启动新服务 ----------
echo "[5/5] 启动新服务..."
nohup python -m uvicorn app.main:app --host "$HOST" --port "$PORT" \
    > /tmp/ai-cs-bot.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > /tmp/ai-cs-bot.pid
echo "  -> 服务已启动 (PID: $NEW_PID)"
echo "  -> 日志文件: /tmp/ai-cs-bot.log"
echo ""

# 等待服务就绪
echo "等待服务启动..."
for i in $(seq 1 10); do
    if curl -s "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1; then
        echo ""
        echo "=========================================="
        echo "  部署成功！"
        echo "  访问地址: http://1.12.55.192:${PORT}"
        echo "  本机访问: http://127.0.0.1:${PORT}"
        echo "  查看日志: tail -f /tmp/ai-cs-bot.log"
        echo "  停止服务: kill \$(cat /tmp/ai-cs-bot.pid)"
        echo "=========================================="
        exit 0
    fi
    printf "."
    sleep 1
done

echo ""
echo "=========================================="
echo "  警告: 服务可能未正常启动"
echo "  请检查日志: cat /tmp/ai-cs-bot.log"
echo "=========================================="
exit 1
