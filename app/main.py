"""
FastAPI 应用入口
================
启动方式（在项目根目录 ai-cs-bot 下执行）：
    uvicorn app.main:app --reload --port 8000

启动后访问 http://localhost:8000/health 可看到健康检查返回。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.api.routes import router as api_router

app = FastAPI(
    title="电商售后智能客服机器人",
    description="具备 RAG 知识库、工具调用 Agent、多轮记忆、人工转接的智能客服",
    version="0.1.0",
)

# 允许前端跨域访问（后续前端页面会用到）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """健康检查接口：确认服务是否正常运行。"""
    return {
        "status": "ok",
        "service": "ai-cs-bot",
        "version": "0.1.0",
    }


# 前端聊天界面
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/")
async def index():
    """返回聊天界面首页。"""
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


# 注册业务路由
app.include_router(api_router)

# 后续步骤会在这里注册更多路由：
#   /api/chat/stream —— 流式聊天（第 7 步）
#   /api/handoff     —— 人工转接（第 6 步）
